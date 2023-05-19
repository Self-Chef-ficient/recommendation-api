from flask_cors import CORS
from flask import Flask, request, render_template,redirect,session
import pandas as pd
from neo4j import GraphDatabase
from autocorrect import Speller
from nltk.stem import WordNetLemmatizer
import nltk 
import os
import random
nltk.download('punkt')
nltk.download('wordnet')

lemmatizer = WordNetLemmatizer()
spell = Speller(lang='en')
def parse_new_ingredient(ingredient):
    ing_token = ".*"+" ".join([lemmatizer.lemmatize(spell(x.lower())) for x in ingredient.split()])+".*"
    return ing_token



class Neo4jConnection:
    
    def __init__(self, uri, user, pwd):
        self.__uri = uri
        self.__user = user
        self.__pwd = pwd
        self.__driver = None
        try:
            self.__driver = GraphDatabase.driver(self.__uri, auth=(self.__user, self.__pwd))
        except Exception as e:
            print("Failed to create the driver:", e)
        
    def close(self):
        if self.__driver is not None:
            self.__driver.close()
        
    def query(self, query, db=None):
        assert self.__driver is not None, "Driver not initialized!"
        session = None
        response = None
        try: 
            session = self.__driver.session(database=db) if db is not None else self.__driver.session() 
            response = list(session.run(query))
        except Exception as e:
            print("Query failed:", e)
        finally: 
            if session is not None:
                session.close()
        return response

url = os.environ.get('NEO4J_URL')
pwd = os.environ.get('NEO4J_PWD')
user = os.environ.get('NEO4J_USER')
conn = Neo4jConnection(uri=url, user=user, pwd=pwd)
ingredient_query_map = {
                    'onions' : '.*onion.*',
                    'carrots' : '.*carrot.*',
                    'tomatoes' : '.*tomato.*',
                    'cauliflower' : '.*cauliflower.*',
                    'mushroom' : '.*mushroom.*',
                    'avocados' : '.*avocado.*',
                    'broccoli' : '.*broccoli.*',
                    'coconut' : '.*coconut.*', 
                    'spinach' : '.*spinach.*', 
                    'seaweed' : '.*seaweed.*', 
                    'milk' : '.*milk.*', 
                    'cinnamon' : '.*cinnamon.*', 
                    'ginger' : '.*ginger.*', 
                    'cheese' : '.*cheese.*', 
                    'garlic' : '.*garlic.*', 
                    'coffee' : '.*coffee.*',
                    'bacon' : '.*bacon.*', 
                    'chicken' : '.*chicken.*',
                    'fish' : '.*salmon.*|.*tuna.*',
                    'shrimp' : '.*shrimp.*',
                    'pork' : '.*pepperoni.*|.*ham.*',
                    'bananas' : '.*banana.*', 
                    'berries' : '.*berr.*', 
                    'pineapple' : '.*pineapple.*',
                    'orange' : '.*orange.*', 
                    'mango' : '.*mango.*',
                    'black beans' : '.*black beans.*',
                    'rice' : '.*rice.*',
                    'oats' : '.*oat.*', 
                    'quinoa' : '.*quinoa.*'
                }

def extract_ings(quiz_answers):
    liked_ings = []
    disliked_ings = []
    for k,v in quiz_answers.items():
        if v == 'liked':
            liked_ings.append(k)
        else:
            disliked_ings.append(k)
    return liked_ings, disliked_ings

def get_db_query(liked_ings,disliked_ings,uid):
    like_string = ''
    dislike_string = ''
    if len(liked_ings) != 0:
        try:
            like_string += str(ingredient_query_map[liked_ings[0]])
        except:
            like_string += parse_new_ingredient(liked_ings[0])
        for i in range(1,len(liked_ings)):
            try:
                like_string += str('|'+str(ingredient_query_map[liked_ings[i]]))
            except:
                like_string += '|'+parse_new_ingredient(liked_ings[i])
    else:
        like_string = '.*'
    if len(disliked_ings) != 0:
        try:
            dislike_string += str(ingredient_query_map[disliked_ings[0]])
        except: 
            dislike_string += parse_new_ingredient(disliked_ings[0])
            for i in range(1,len(disliked_ings)):
                try:
                    dislike_string += str('|'+str(ingredient_query_map[disliked_ings[i]]))
                except:
                    dislike_string += '|'+parse_new_ingredient(disliked_ings[i])
        
    query_string = "MATCH (i:Ingr)<-[r1:uses]-(d:Food) \
                    WHERE i.ingrName =~ '"+like_string+"'\
                        AND \
                        NOT EXISTS {  \
                        MATCH (x:Ingr)<-[:uses]-(d) \
                        WHERE x.name =~ '"+dislike_string+"' \
                      } \
                    WITH gds.alpha.graph.project( \
                      '"+uid+"', \
                      d, \
                      i, \
                      {}, \
                      {}, \
                      {undirectedRelationshipTypes: ['*']} \
                    ) as g \
                    CALL gds.pageRank.stream('"+uid+"') \
                    YIELD nodeId, score \
                    RETURN gds.util.asNode(nodeId) AS name, score \
                    ORDER BY score DESC"
    return query_string

def get_recs(results):
    rows = []
    recs = []
    count = 0
    for i in range(len(results)):
        type_rec = list(results[i][0].labels)[0]
        if type_rec == 'Food':
            name = dict(results[i][0])['foodID']
            score = results[i]['score']
            rows.append({'name':name,'score':score})
    result_df = pd.DataFrame(rows)
    grouped_recs = result_df.groupby('score')
    while (count<5):
        for g in grouped_recs.groups:
            rec = random.choice(grouped_recs.get_group(g)['name'].values)
            if rec not in recs:
                recs.append(rec)
            count += 1
            if count<=5:
                break
    return recs

app = Flask(__name__)
CORS(app)

@app.route('/getRecs', methods=['GET', 'POST'])
def getRecs():
    if request.method == 'GET':
        return "working"
    if request.method == 'POST':
        input_json = request.get_json()
        liked_ings, disliked_ings = extract_ings(input_json['quiz'])
        db_query = get_db_query(liked_ings, disliked_ings,input_json['user'])
        results = conn.query(db_query)
        delete_graph = conn.query("CALL gds.graph.drop('"+input_json['user']+"') YIELD graphName;")
        final_recs = get_recs(results)
        res = {}
        res['user'] = input_json['user']
        res['recommendations'] = final_recs
        return res

if __name__ == '__main__':
	app.run(debug=False)
