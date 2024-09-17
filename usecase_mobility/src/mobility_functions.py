import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from shapely.geometry import LineString, shape, Point
from shapely import to_geojson
import zipfile
import os
import osmnx as ox
import networkx as nx
from typing import List
import h3


def grid_lookup(G:nx.classes.multidigraph.MultiDiGraph) -> pd.DataFrame:
    nodes = ox.graph_to_gdfs(G, edges=False)
    #nodes_dict = nodes.to_dict()

    lng_min, lng_max, lat_min, lat_max = nodes['x'].min(), nodes['x'].max(), nodes['y'].min(), nodes['y'].max()
    lat_array = np.arange(lat_min-0.02,lat_max+0.02,0.001)
    lng_array = np.arange(lng_min-0.02,lng_max+0.02,0.0015)

    #h3_target = 13
    h3_start = 8
    h3_indexes = set()
    for lat in lat_array:
        for lng in lng_array:
            h3_index = h3.geo_to_h3(lat, lng, h3_start)
            h3_indexes.add(h3_index)

    edge_grid_df = pd.DataFrame({'h3':[], 'edge':[], 'distance':[]})
    h3_test = list(h3_indexes)#[:100]
    for cell in h3_test:
        lat = h3.h3_to_geo(cell)[0]
        lng = h3.h3_to_geo(cell)[1]
        
        cell_children = []
        sublayer_1 = list(h3.h3_to_children(cell))
        for child_i in sublayer_1:
            sublayer_2 = list(h3.h3_to_children(child_i))
            for child_ij in sublayer_2:
                sublayer_3 = list(h3.h3_to_children(child_ij))
                for child_ijk in sublayer_3:
                    sublayer_4 = list(h3.h3_to_children(child_ijk))
                    for child_ijkl in sublayer_4:
                        sublayer_5 = list(h3.h3_to_children(child_ijkl))
                        cell_children.extend(sublayer_5)
        lats = [h3.h3_to_geo(x)[0] for x in cell_children]
        lngs = [h3.h3_to_geo(x)[1] for x in cell_children]
        edge_tuples = ox.nearest_edges(G,lngs,lats,return_dist=True)
        df_i = pd.DataFrame({'h3':cell_children, 'edge':edge_tuples[0], 'distance':edge_tuples[1]})
        df_i = df_i[df_i['distance'] <= 0.0005]
        edge_grid_df = pd.concat([edge_grid_df,df_i], axis=0, ignore_index=True)
 
    edge_grid_df['edge'] = edge_grid_df['edge'].apply(lambda x: (x[0],x[1]))

    #name_shape_df = get_name_shape(G)
    #edge_grid_df = pd.merge(edge_grid_df,name_shape_df,how='left',on='edge')

    return edge_grid_df


def get_name_shape(G:nx.classes.multidigraph.MultiDiGraph) -> pd.DataFrame:
    nodes = ox.graph_to_gdfs(G, edges=False)
    nodes_dict = nodes.to_dict()

    G_edges = list(G.edges())
    G_shapes = []
    G_names = []
    for edge in G_edges:
        try:
            name_i = G.get_edge_data(edge[0],edge[1])[0]['name']
            G_names.append(name_i)
        except:
            G_names.append(None)
        try:
            shape_i = G.get_edge_data(edge[0],edge[1])[0]['geometry']
            G_shapes.append(shape_i)
        except:
            start = (nodes_dict['x'][edge[0]],nodes_dict['y'][edge[0]])
            end = (nodes_dict['x'][edge[1]],nodes_dict['y'][edge[1]])
            G_shapes.append(LineString([start,end]))

    #G_edges = [str(edge) for edge in G_edges]
    #G_shapes = [str(edge) for edge in G_shapes]
    #G_names = [str(edge) for edge in G_names]

    name_shape_df = pd.DataFrame({'edge':G_edges, 'name':G_names, 'shape':G_shapes})
    #edge_name_dict = dict(zip(G_edges,G_names))
    #edge_shape_dict = dict(zip(G_edges,G_shapes))
    return name_shape_df