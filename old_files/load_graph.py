import networkx as nx
import ijson
import math
from scipy.spatial import KDTree
import numpy as np
import graph_fill

import os
from sqlalchemy import Column, Integer, String, JSON, Float, ForeignKey, Time, Date, Boolean, create_engine , inspect , text
from sqlalchemy.orm import declarative_base, sessionmaker


Base = declarative_base()

class Station(Base):
    __tablename__ = 'stations'
    id = Column(Integer, primary_key=True)

class Graph(Base):
    __tablename__ = "graph"

    id = Column(Integer, primary_key=True)
    departure = Column(Integer, ForeignKey("stations.id"))
    arrival = Column(Integer, ForeignKey("stations.id"))
    path = Column(JSON)



class GraphLoader:
    def __init__(self):
        self.graph = nx.Graph()
        self.node_coords = {}
        self.stations = []
        self.station_node_map = {}

    def load_data(self, osm_file="poland.json"):
        count = 0
        with open(osm_file, 'rb') as f:
            elements = ijson.items(f, 'elements.item')
            for el in elements:
                if el.get("type") == "way" and "geometry" in el:
                    tags = el.get("tags", {})
                    if "railway" in tags:
                        points = [(pt["lat"], pt["lon"]) for pt in el["geometry"]]
                        for i in range(len(points) - 1):
                            u = points[i]
                            v = points[i+1]
                            dist = math.hypot(u[0]-v[0], u[1]-v[1])
                            maxspeed=tags.get("maxspeed")
                            self.graph.add_edge(u, v, weight=dist , maxspeed=maxspeed)
                        count += 1
                        if count % 5000 == 0:
                            print(f"  Processed {count} ways...")
        print(f"Graph loaded: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")

    def load_stations(self , result):
        for row in result:
            el = dict(row._mapping)
            self.stations.append({
                "id": el["id"],
                "name": el["name"],
                "lat": el["latitude"],
                "lon": el["longitude"]
            })


    def snap_stations(self ):
        if self.graph.number_of_nodes() == 0:
            print("Graph is empty. Cannot snap.")
            return

        graph_nodes = list(self.graph.nodes())
        graph_nodes_array = np.array(graph_nodes)

        tree = KDTree(graph_nodes_array)
        snapped_count = 0
        for st in self.stations:
            dist, index = tree.query([st["lat"], st["lon"]])

            if dist > 0.1:
                pass

            nearest_node = tuple(graph_nodes[index])
            self.station_node_map[st["id"]] = nearest_node
            snapped_count += 1


    def find_path(self, start_station_id, end_station_id):
        start_node = self.station_node_map[start_station_id]
        end_node = self.station_node_map[end_station_id]
        try :
            path = nx.shortest_path(self.graph, source=start_node, target=end_node, weight="weight")
        except nx.NetworkXNoPath:
            print(f"No path found between {start_station_id} and {end_station_id}")
            return None
        return path

    def load_graph_to_db(self):
        used_pairs = set()
        for i in self.stations:
            for j in self.stations:
                s = i['id']
                t = j['id']
                if s != t and (s, t) not in used_pairs and (t, s) not in used_pairs:
                    path = self.find_path(s, t)
                    yield (s, t, path)



current_folder = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_folder, 'EuroTicket.db')

engine = create_engine(f"sqlite:///{db_path}")
Session = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


def upload_to_db(start_id, end_id, path):
    session = Session()
    try:
        existing_route = session.query(Graph).filter_by(departure=start_id, arrival=end_id).first()
        if existing_route:
            existing_route.path = path
            session.commit()
            print(f"Updated route {start_id}->{end_id}")
        else:
            new_route = Graph(
                departure=start_id,
                arrival=end_id,
                path=path
            )
            session.add(new_route)
            session.commit()
            print(f"Uploaded route {start_id}->{end_id}")
    except Exception as e:
        session.rollback()
        print(f"Error uploading route {start_id}->{end_id}: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    loader = GraphLoader()
    loader.load_data()

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    print("Tables found:", table_names)

    with engine.connect() as connection:
        query = text("SELECT * FROM stations")
        result = connection.execute(query)
        loader.load_stations(result)

    loader.snap_stations()

    all_pairs = graph_fill.get_adjacent_pairs(Session())
    for i , (x, y) in enumerate(all_pairs):
        #print(i , x , y)
        p = loader.find_path(x, y)
        upload_to_db(x, y, [(float(x), float(y)) for x, y in p])
