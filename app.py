from flask import Flask, request, send_file,jsonify,render_template
from flask_pymongo import MongoClient, ObjectId
import redis
import json
import time
from flask_cors import CORS


app = Flask(__name__)
CORS(app)
# MongoDB connection
#mongo_url = 'mongodb+srv://test:zxiEwhw7LJvHOUC9@cluster.5xje4sy.mongodb.net/?retryWrites=true&w=majority'
mongo_client = MongoClient('mongodb://admin:admin@mongodb:27017?authSource=admin&retryWrites=true&w=majority')
db = mongo_client.matav
col = db.events

# Redis connection
redis_client =redis.Redis(host='redis', port=6379, db=0)
# Routes
@app.route('/')
def index():
    return send_file('templates/index.html')

@app.route('/getEvent/<column>/<value>')
def get_event(column, value):
    if column == '':
        return "Column can't be empty"

    if value != '':
        data = {}
        cache_key = f"{column}:{value}"
        cached_data = redis_client.get(cache_key)
        if cached_data:
            print("From Redis")
            data = json.loads(cached_data)
        else:
            time.sleep(1)
            datas = []
            if(column == '_id'):
                value = ObjectId(value)
            response = col.find({column: value})
            for document in response:
                document['_id'] = str(document['_id'])
                datas.append(document)

            info = getInterestingInfo(datas)
            data = info
            redis_client.set(cache_key, json.dumps(info),30)
            
        return render_template('output.html', data=data)
    
    else:
        return "Value can't be empty"
@app.route('/getEventInfo')
def get_event_info():  
    data = []
    cache_key = "getInfo"
    cached_data = redis_client.get(cache_key)
    if cached_data:
        print("from Redis")
        data = json.loads(cached_data)
    else:
        time.sleep(1)
        response = col.aggregate([ {"$group" : {
                        "_id": "$type",
                        "count": { "$sum": 1 },
                        "avgTimestamp": { "$avg": { "$toDouble": "$timeStamp" } },
                        "mostFrequentIds": { "$push": "$id" },
                    }},
                    {
                    "$project": {
                        "_id": 1,
                        "count": 1,
                        "avgTimestamp": 1,
                        "mostFrequentIds": { "$slice": ["$mostFrequentIds", 5] }
                    }
                    }])
        for document in response:
            data.append(document)
        redis_client.set(cache_key, json.dumps(data),30)
    return render_template('vypis.html', events=data)



@app.route('/event', methods=['POST'])
def post_event():
    try:
        data = request.get_json()
        col.insert_one(data)
    except Exception as e:
         print(e)
         
    return jsonify({'ok': True, 'message': 'Event created successfully!'})

def getInterestingInfo(data):
    result = dict()

    rozdelenaData = {}
    for obj in data:
        for nazev, hodnota in obj.items():
            if nazev not in rozdelenaData:
                rozdelenaData[nazev] = []
            if isinstance(hodnota, dict):
                for key, value in hodnota.items():
                    if f"{nazev}.{key}" not in rozdelenaData:
                        rozdelenaData[f"{nazev}.{key}"] = []
                    rozdelenaData[f"{nazev}.{key}"].append(value)

            elif str(hodnota).isdigit():
                hodnota = int(hodnota)
  
            rozdelenaData[nazev].append(hodnota)

    for name in rozdelenaData:
        hodnoty = rozdelenaData[name]
        if len(hodnoty) == 0:
            continue
        try:
            if are_all_digits(hodnoty):
                result[name] = {
                    'max': max(hodnoty),
                    'min': min(hodnoty),
                    'most_common': most_common(hodnoty),
                    'avg': sum(hodnoty) / len(hodnoty),
                    'count': len(hodnoty),
                #  'values': hodnoty
                    
                }
            elif not are_any_dicts(hodnoty):
                result[name] = {
                    'count': len(hodnoty),
                    'most_common': most_common(hodnoty),
                #   'values': hodnoty
                }
            #To be continued práce se slovníky a jejich statistika
        except Exception as e:
            print(e)

    return result

def most_common(lst):
    return max(lst, key=lst.count)

def are_all_digits(lst):
    return all(str(item).isdigit() for item in lst)

def are_any_dicts(lst):
    return any(isinstance(item, dict) for item in lst)

if __name__ == '__main__':
   app.run(debug=True)
    
    
    
    
    
