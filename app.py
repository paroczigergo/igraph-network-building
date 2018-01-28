import os
import json
import cairo
import redis
from igraph import *
from flask import Flask,request
import sqlite3
from pathlib import Path
import re
import logging

app = Flask(__name__)

# configure the logging method for debug
logger = logging.getLogger('info')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


def regexp(expr, item):
    """
    This function is a part of the REGEXP sqlite function's implementation
    for using regex in an sqlite query
    """
    reg = re.compile(expr)
    return reg.search(item) is not None

class FileStructureProcessor:
    """
    This class manages the processing of a (sub-)folder/files structure 
    (starting from an arbitrary folder) of the local drive 
    into a Graph object with file informations.
    """

    def search_from_sqlite(self, key):
        """Searching in Graph object by name, using regex"""
        key = ('.*' +key+ '.*',)
        conn = get_sqlite()
        c = conn.cursor()
        conn.create_function("REGEXP", 2, regexp)
        c.execute('SELECT * FROM vertices WHERE name REGEXP ? ', key)
        results = c.fetchall()

        return json.dumps([{
            'name': r[1],
            'size': r[3],
            'parent': r[2],
            'last_accessed': r[4],
            'last_modified': r[5]} for r in results])

    def search_from_igraph(self, key):
        """Searching in Graph object by name, using build-in graph search method"""
        results =self.graph.vs.select(name_in=key)
        return json.dumps([{
            'name': r["name"],
            'size': r["size"],
            'parent': r["parent"],
            'last_accessed': r["last_accessed"],
            'last_modified': r["last_modified"]} for r in results])

    def create_graph(self,root_path):
        """Create Graph object of file structure starting from the given root"""
        graph = self.graph

        #get the path lists recursively from the root directory 
        path_list = sorted(Path(root_path).rglob('*'))
        # create the necessary amount of vertices 
        graph.add_vertices(len(path_list)+1)
        
        # these list will be used for inserting to sqlite database
        vertices = []
        edges = []

        # now the edges have to be created, and the vertices need the file informations
        # first is the root vertex
        temp=graph.vs[0]
        temp["name"]=root_path
        temp["parent"]=""
        temp["size"]=os.stat(root_path).st_size
        temp["last_modified"]=os.stat(root_path).st_mtime
        temp["last_accessed"]=os.stat(root_path).st_atime
      
        vertices.append((0,temp["name"],temp["parent"],temp["size"],temp["last_modified"],temp["last_accessed"]))

        # walking through the paths, the vertices get the informations, and the egdes will be created
        for i, file in enumerate(path_list):
            temp=graph.vs[i+1]
            temp["name"]=file.as_posix()
            temp["parent"]=file.parent.as_posix()
            temp["size"]=os.stat(file).st_size
            temp["last_modified"]=os.stat(file).st_mtime
            temp["last_accessed"]=os.stat(file).st_atime
            vertices.append((temp.index,temp["name"],temp["parent"],temp["size"],temp["last_modified"],temp["last_accessed"]))
            
            parent_id=graph.vs.find(name=temp["parent"]).index
            # Egde is defined beetween the current vertex and its parent
            graph.add_edges([(i+1,parent_id)])
            edges.append((i+1,parent_id))

        # save the created Graph object into the connected redis database as JSON
        cache= get_redis()
        cache.execute_command('JSON.SET', 'vertices_name','.',json.dumps(self.graph.vs["name"]))
        cache.execute_command('JSON.SET', 'vertices_parent','.',json.dumps(self.graph.vs["parent"]))
        cache.execute_command('JSON.SET', 'vertices_size','.',json.dumps(self.graph.vs["size"]))
        cache.execute_command('JSON.SET', 'vertices_last_modified','.',json.dumps(self.graph.vs["last_modified"]))
        cache.execute_command('JSON.SET', 'vertices_last_accessed','.',json.dumps(self.graph.vs["last_accessed"]))
        cache.execute_command('JSON.SET', 'edges','.',json.dumps(self.graph.get_edgelist()))

        # save the created Graph object into the connected sqlite database 
        conn = get_sqlite()
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS vertices')
        c.execute('DROP TABLE IF EXISTS edges')
        c.execute('CREATE TABLE vertices (id, name, parent, size, last_modified, last_accessed)')
        c.execute('CREATE TABLE edges (start, end)')
        c.executemany('INSERT INTO vertices VALUES (?,?,?,?,?,?)', vertices)
        c.executemany('INSERT INTO edges VALUES (?,?)', edges)
        conn.commit()

        # optionally create image from the Graph object
        # unfortunatelly this feature not working correctly now
        plot(graph,"plot.png", layout="tree")
    
    def fetch_from_sqlite(self):
        """ Fetch the saved Graph from sqlite database"""
        conn = get_sqlite()
        c = conn.cursor()
        c.execute('SELECT * FROM vertices ORDER BY id')
        vertices =c.fetchall()
        c.execute('SELECT * FROM edges')
        edges =c.fetchall()
        logger.info(egdes)
        conn.commit()

        self.graph.add_vertices(len(vertices))
        for one in vertices:
            id =int(one[0])
            self.graph.vs[id]["name"] = one[1]
            self.graph.vs[id]["parent"] = one[2]
            self.graph.vs[id]["size"] = one[3]
            self.graph.vs[id]["last_modified"] = one[4]
            self.graph.vs[id]["last_accessed"] = one[5]

        for one in edges:
            self.graph.add_edges([(one[0],one[1])])

    def fetch_from_redis(self):
        """ Fetch the saved Graph from redis database"""
        cache= get_redis()
        egdes_list = json.loads(cache.execute_command('JSON.GET', 'edges'))
        self.graph= Graph([(one[0],one[1]) for one in egdes_list])
        self.graph.vs["name"]=json.loads(cache.execute_command('JSON.GET', 'vertices_name'))
        self.graph.vs["parent"]=json.loads( cache.execute_command('JSON.GET', 'vertices_parent'))
        self.graph.vs["size"]=json.loads( cache.execute_command('JSON.GET', 'vertices_size'))
        self.graph.vs["last_modified"]=json.loads( cache.execute_command('JSON.GET', 'vertices_last_modified'))
        self.graph.vs["last_accessed"]=json.loads( cache.execute_command('JSON.GET', 'vertices_last_accessed'))

    def get_graph(self):
        """ Get the saved Graph's edges as JSON"""
        return json.dumps(self.graph.get_edgelist(), separators=(',',':'))

    def __init__(self, source="redis"):
        """The entry of the class for initialize the Graph"""
        self.graph = Graph()

        # checking for the saved data in the connected databases
        is_sqlite_exists=get_sqlite().cursor().execute('SELECT count(*) FROM sqlite_master WHERE name="edges"').fetchone()[0]
        is_redis_exists=0 if get_redis().execute_command('JSON.GET', "edges")== None else 1

        # choose the source of the Graph 
        if is_sqlite_exists and source=="sqlite":
            self.fetch_from_sqlite()
        elif is_redis_exists and source=="redis":
            self.fetch_from_redis()   
        else:
            self.create_graph(".")
       

"""
   The following endpoints are mapped by the Flask webserver:
"""

@app.route('/graph/redis')
def get_from_redis():
    """ Get the JSON representation of the Graph from redis """
    graph = FileStructureProcessor()
    return graph.get_graph()

@app.route('/graph/sqlite')
def get_from_sqlite():
    """ Get the JSON representation of the Graph from sqlite """
    graph = FileStructureProcessor("sqlite")
    return graph.get_graph()

@app.route('/graph/create')
def create():
    """ Creating Graph object from file structure, and get its JSON representation """
    # for clean test cases, first the available databases will be flushed
    os.remove('igraph.db')
    get_redis().flushdb()
    graph = FileStructureProcessor()
    return graph.get_graph()

@app.route('/search/sqlite')
def search_from_sqlite():
    """Searching in Graph object by name, using regex"""
    key = request.args.get('key')
    graph = FileStructureProcessor("sqlite")
    return graph.search_from_sqlite(key)

@app.route('/search/igraph')
def search_from_igraph():
    """Searching in Graph object by name, using build-in graph search method"""
    key = request.args.get('key')
    graph = FileStructureProcessor()
    return graph.search_from_igraph(key)

def get_sqlite():
    """ Get the connection of the local sqlite database """
    return sqlite3.connect('igraph.db')

def get_redis():
    """ Get the connection of the connected redis database """
    return redis.StrictRedis(host='redis', port=6379)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)