import os
import sys
import argparse
import logging as log
import numpy as np
import networkx as nx
from networkx.algorithms import centrality as nxc
import pandas as pd
import graph_analysis as ga
import path_analysis as pa

def get_hubs(G, **kwargs):
    """Returns a dictionary of degree values for all node."""

    degree_tuple = G.degree()
    hubs = {n : (d if d >= kwargs["hub"] else 0) for n, d in degree_tuple}
    return hubs

def get_degree_cent(G, **kwargs):
    """Returns a dictionary of degree centrality values for each node."""

    centrality_dict = nxc.degree_centrality(G)
    return centrality_dict

def get_graph_without_glycine(G, identifiers, residue_names):
    """Takes in a graph, a list of nodes for the graph and a list of
    residues corresponding to each node. Returns a graph without any 
    nodes corresponding to Glycine.
    """
    # get dictionary of node:res
    node_dict = dict(zip(identifiers, residue_names))
    # get all nodes which correspond to glycine
    glycine_nodes = [node for node, res in node_dict.items() if res == "GLY"]
    # create new graph without glycines
    H = G.copy()
    H.remove_nodes_from(glycine_nodes)
    return H

def fill_dict(G, cent_dict):
    """Takes in a graph and a dictionary of centrality values. Returns a
    new dictionary of centrality values containing each node in the 
    graph. If the node is not in the given dictionary, it has a value of
    0 or else it has the value in the given dictionary.
    """

    return {n : (cent_dict[n] if n in cent_dict else 0) for n in G.nodes()}

def get_betweeness_cent(G, **kwargs):
    """Returns a dictionary of betweenness centrality values for all node."""

    # Need to consider if endpoints should be used or not
    H = get_graph_without_glycine(G, kwargs["identifiers"], kwargs["residue_names"])
    centrality_dict = nxc.betweenness_centrality(G = H,
                                                 normalized = kwargs["normalized"],
                                                 weight = kwargs["weight"],
                                                 endpoints = kwargs["endpoints"])
    centrality_dict = fill_dict(G, centrality_dict)
    return centrality_dict

def get_closeness_cent(G, **kwargs):
    """Returns a dictionary of closeness centrality values for all node."""

    H = get_graph_without_glycine(G, kwargs["identifiers"], kwargs["residue_names"])
    centrality_dict = nxc.closeness_centrality(G = G, distance = kwargs["weight"])
    centrality_dict = fill_dict(G, centrality_dict)
    return centrality_dict

def get_eigenvector_cent(G, **kwargs):
    """Returns a dictionary of eigenvector centrality values for all node."""

    centrality_dict = nxc.eigenvector_centrality_numpy(G = G, 
                                                       weight = kwargs["weight"])
    return centrality_dict

def get_current_flow_betweenness_cent(G, **kwargs):
    """Returns a dictionary of current flow betweenness centrality
    values. This is the same as calculating betweenness centrality using
    random walks instead of shortest paths.
    """

    centrality_dict = nxc.current_flow_betweenness_centrality(\
                                G = G, 
                                normalized = kwargs["normalized"],
                                weight = kwargs["weight"])
    return centrality_dict

def get_current_flow_closeness_cent(G, **kwargs):
    """Returns a dictionary of current flow closeness centrality
    values.
    """

    centrality_dict = nxc.current_flow_closeness_centrality(\
                                G = G,
                                weight = kwargs["weight"])
    return centrality_dict

def reorder_edge_names(edge_dict):
    """Takes in a dictionary where the keys are edge names and returns 
    a dictionary with where the keys are sorted edge names.
    """

    # lambda function takes in an edge e.g. ("A99", "A102"), removes all
    # non numeric characters and converts to an integer
    node_to_int = lambda node: int(''.join([n for n in node if n.isdigit()]))
    # sort the edge names by their corresponding node number (99 and 102) 
    # and convert the sorted edge name to a string
    reordered_dict = {",".join(sorted(edge, key = node_to_int)): value \
                        for edge, value in edge_dict.items()}
    return reordered_dict

def get_edge_betweenness_cent(G, **kwargs):
    """Returns a dictionary of edge betweenness centrality values."""
    
    centrality_dict = nxc.edge_betweenness_centrality(G = G,
                                                      normalized = kwargs["normalized"],
                                                      weight = kwargs["weight"])
    reordered_dict = reorder_edge_names(centrality_dict)
    return reordered_dict

def get_edge_current_flow_betweenness_cent(G, **kwargs):
    """Returns a dictionary of edge current flow betweenness centrality 
    values. This is the same as calculating edge betweenness centrality 
    using random walks instead of shortest paths.
    """
    
    centrality_dict = nxc.edge_current_flow_betweenness_centrality(\
                                    G = G,
                                    normalized = kwargs["normalized"],
                                    weight = kwargs["weight"])
    reordered_dict = reorder_edge_names(centrality_dict)
    return reordered_dict

def get_centrality_dict(cent_list, function_map, graph, **kwargs):
    """Returns two dictionaries. For the first dictionary, the key is the 
    name of a node centrality measure and the value is a dictionary of 
    centrality values for each node e.g. {degree: {A: 0.1, B:0.7, ...}, 
    betweenness: {...}, ...}. For the second dictionary, the key is the 
    name of an edge centrality measure and the value is a dictionary of 
    centrality values for each edge, similar to the first dictionary.
    """

    # List of measures that require a connected graph
    connected_measures = ["current_flow_betweenness", "current_flow_closeness", 
                          "edge_current_flow_betweenness"]
    # Get all components
    components = nx.algorithms.components.connected_components(graph)
    # reverse sort components by size
    components = sorted(components, key = lambda x: len(x), reverse = True)
    # List of subgraphs for each connected component with 3 nodes or more
    subgraphs = [graph.subgraph(component).copy() for component in components 
                 if len(component) > 2]
    # Intialize output dictionaries
    node_dict = {}
    edge_dict = {}
    identifiers = kwargs["identifiers"]
    res_name = kwargs["residue_names"]
    # Add residue names to node_dict if available
    if res_name is not None:
        node_dict["name"] = {identifiers[i]: res_name[i] for i in range(len(identifiers))}
    sys.stdout.write("Calculating:\n")
    for name in cent_list:
        # Print which measure is being calculated
        p_name = name.replace("_", " ")
        sys.stdout.write(f"{p_name}\n")
        # Choose whether to insert to node_dict or edge_dict
        insert_dict = edge_dict if "edge" in name else node_dict
        # For the measures in the list, calculate values for each subgrapg
        if name in connected_measures:
            for n, subgraph in enumerate(subgraphs):
                # Get dictionary using the function map
                cent_dict = function_map[name](G = subgraph, **kwargs)
                # Fill in missing nodes with 0 for node dicts
                if "edge" not in name:
                    cent_dict = fill_dict(graph, cent_dict)
                # Add to dictionary with a name corresponding to the subgraph
                insert_dict[f"{name}_{n+1}"] = cent_dict
        else:
            # Calculate and add the measures that do not require connected graphs
            cent_dict = function_map[name](G = graph, **kwargs)
            insert_dict[name] = cent_dict
    return node_dict, edge_dict

def write_table(fname, centrality_dict, sort_by):
    """Takes in a dictionary of dictionaries and saves a file where each 
    row consists of a node and its corresponding centrality values.
    """

    # Remove any file extensions
    fname = os.path.splitext(fname)[0]
    # Transform dict to df
    table = pd.DataFrame(centrality_dict)
    # Find if row name should be node or edge
    row_name = "edge" if "," in table.index[0] else "node"
    table = table.rename_axis(row_name)
    # Only sort if node/edge is not specified
    if not(sort_by == "node" or sort_by == "edge"):
        table = table.sort_values(by=[sort_by], ascending = False)
    # Save file
    # remove na_rep to have an empty representation
    table.to_csv(f"{fname}.txt", sep = "\t", na_rep= "NA") 

def write_pdb_files(centrality_dict, pdb, fname):
    """Save a pdb file for every centrality measure in the input 
    centrality dictionary.
    """

    for cent_name, cent_dict in centrality_dict.items():
        # Ignore residue name column
        if cent_name != "name":
            # Create input array
            cent_array = np.array([val for val in cent_dict.values()])
            # Replace column and save PDB file
            ga.replace_bfac_column(pdb, cent_array, f"{fname}_{cent_name}.pdb")

def save_matrix(centrality_dict, identifiers):
    """Takes in a dictionary of dictionary and saves a matrix file for
    each inner dictionary.
    """

    for name, edge_dict in centrality_dict.items():
        # Create a graph for each inner dictionary
        G = nx.Graph()
        G.add_nodes_from(identifiers)
        # create list of (node1, node2, edge weight)
        edges = [(edge[0], edge[1], cent) for edge, cent in edge_dict.items()]
        G.add_weighted_edges_from(edges)
        # Convert graph to matrix
        matrix = nx.to_numpy_matrix(G)
        np.savetxt(f"{name}.dat", matrix)

def main():

    ######################### ARGUMENT PARSER #########################

    description = "Centrality analysis module for PyInteraph. It can be used " \
                  "to calculate hubs, node centralities, group centralities " \
                  "and edge centralities."
    parser = argparse.ArgumentParser(description = description)

    i_helpstr = ".dat file matrix"
    parser.add_argument("-i", "--input-dat",
                        dest = "input_matrix",
                        help = i_helpstr,
                        type = str)

    r_helpstr = "Reference PDB file"
    parser.add_argument("-r", "--pdb",
                        dest = "pdb",
                        help = r_helpstr,
                        default = None,
                        type = str)

    # Centrality types
    node = ["hubs", "degree", "betweenness", "closeness", "eigenvector", 
            "current_flow_betweenness", "current_flow_closeness"]
    edge = ["edge_betweenness", "edge_current_flow_betweenness"]
    all_cent = node + edge

    c_choices = all_cent + ["all", "node", "edge"]
    c_default = None
    c_helpstr = f"Select which centrality measures to calculate: {c_choices} " \
                f"(default: {c_default}). Selecting 'node' will calculate the "\
                f"following centralities: {node}. Selecting 'edge' will " \
                f"calculate the following centralities: {edge}. Selecting " \
                f"'all' will calculate all node and edge centralities."
    parser.add_argument("-c", "--centrality",
                        dest = "cent",
                        nargs = "+",
                        choices = c_choices,
                        default = c_default,
                        help =  c_helpstr)

    b_choices = node
    b_default = "node"
    b_helpstr = f"Sort node centralities. Use the name of the " \
                f"desired measure. The name must match one of the names " \
                f"used in option -c. (default: {b_default})."
    parser.add_argument("-b", "--sort-node",
                        dest = "sort_node",
                        choices = b_choices,
                        default = b_default,
                        help = b_helpstr)

    d_choices = edge
    d_default = "edge"
    d_helpstr = f"Sort edge centralities. Use the name of the " \
                f"desired measure. The name must match one of the names " \
                f"used in option -c. (default: {d_default})."
    parser.add_argument("-d", "--sort-edge",
                        dest = "sort_edge",
                        choices = d_choices,
                        default = d_default,
                        help = d_helpstr)

    n_default = True
    n_helpstr = f"Normalize centrality measures. " \
                f"(default: {n_default})."
    parser.add_argument("-n", "--normalize",
                        dest = "normalized",
                        action = "store_true",
                        default = n_default,
                        help = n_helpstr)

    e_default = False
    e_helpstr = f"Use endpoints when calculating centrality measures. " \
                f"(default: {e_default})."
    parser.add_argument("-e", "--use_endpoints",
                        dest = "endpoints",
                        action = "store_true",
                        default = e_default,
                        help = e_helpstr)

    x_default = 100
    x_helpstr = f"The maximum number of iterations when calculating " \
                f"eigenvector centrality (default: {x_default})."
    parser.add_argument("-x", "--max-iter",
                        dest = "max_iter",
                        default = x_default,
                        type = int,
                        help = x_helpstr)

    t_default = 1e-06
    t_helpstr = f"The tolerance when calculating eigenvector centrality. " \
                f"(default: {t_default})."
    parser.add_argument("-t", "--tolerance",
                        dest = "tol",
                        default = t_default,
                        type = float,
                        help = t_helpstr)

    k_default = 3
    k_helpstr = f"The minimum cutoff for a node to be considered a hub. " \
                f"(default: {k_default})."
    parser.add_argument("-k", "--hub-cutoff",
                        dest = "hub",
                        default = k_default,
                        type = int,
                        help = k_helpstr)

    o_default = "centrality"
    o_helpstr = f"Output file name for centrality measures " \
                f"(default: {o_default}.txt)."
    parser.add_argument("-o", "--centrality-output",
                        dest = "c_out",
                        default = o_default,
                        help = o_helpstr)

    p_default = False
    p_helpstr = f"For each centrality measure calculated, create a PDB file " \
                f"where the bfactor column is replace by the centrality value. " \
                f"(default: {p_default})."
    parser.add_argument("-p", "--pdb_output",
                        dest = "save_pdb",
                        action = "store_true",
                        default = False,
                        help = p_helpstr)

    m_default = False
    m_helpstr = f"For each edge centrality measure calculated, create a .dat " \
                f"file (matrix) containing the centrality values. " \
                f"(default: {m_default})."
    parser.add_argument("-m", "--matrix_output",
                        dest = "save_mat",
                        action = "store_true",
                        default = False,
                        help = m_helpstr)

    args = parser.parse_args()

    # Check user input
    if not args.input_matrix:
        # exit if the adjacency matrix was not speficied
        log.error("Graph adjacency matrix must be specified. Exiting ...")
        exit(1)

    # Load file, build graphs and get identifiers for graph nodes
    identifiers, residue_names, graph = pa.build_graph(fname = args.input_matrix,
                                                       pdb = args.pdb)

    # get graph nodes and edges
    nodes = graph.nodes()
    edges = graph.edges()
    # print nodes
    info = f"Graph loaded! {len(nodes)} nodes, {len(edges)} edges\n" \
           f"Node list:\n{np.array(identifiers)}\n"
    if residue_names is not None:
        info += f"Residue names:\n{np.array(residue_names)}\n"
    sys.stdout.write(info)

    ############################ CENTRALITY ############################

    # Function map of all implemented measures
    function_map = {
        "hubs" : get_hubs,
        "degree" : get_degree_cent, 
        "betweenness" : get_betweeness_cent,
        "closeness" : get_closeness_cent,
        "eigenvector" : get_eigenvector_cent,
        "current_flow_betweenness" : get_current_flow_betweenness_cent,
        "current_flow_closeness" : get_current_flow_closeness_cent,
        "edge_betweenness" : get_edge_betweenness_cent,
        "edge_current_flow_betweenness" : get_edge_current_flow_betweenness_cent
        }
    
    # Get list of all centrality measures
    if args.cent is not None:
        # Find all centralities
        if "all" in args.cent:
            centrality_names = all_cent
        # Find all node centralities
        elif "node" in args.cent:
            centrality_names = node
        # Find all edge centralities
        elif "edge" in args.cent:
            centrality_names = edge
        else:
            # Get list of specified centrality names
            centrality_names = args.cent

        # Check sorting options
        # sorting arg is either node or in centrality names
        if not (args.sort_node == "node" or args.sort_node in centrality_names):
            # expected node names
            expected_names = [name for name in centrality_names if name not in edge]
            err_str = f"The node sorting centrality argument (option -b) must " \
                      f"be one of the following: {', '.join(expected_names)}. Exiting..."
            log.error(err_str)
            exit(1)

        # sorting arg is either edge or in centrality names
        if not (args.sort_edge == "edge" or args.sort_edge in centrality_names):
            # expected edge names
            expected_names = [name for name in centrality_names if name not in node]
            err_str = f"The edge sorting centrality argument (option -d) must " \
                      f"be one of the following: {', '.join(expected_names)}. Exiting..."
            log.error(err_str)
            exit(1)

        # Create dictionary of optional arguments
        kwargs = {"weight" : None,
                  "normalized" : args.normalized,
                  "endpoints" : args.endpoints,
                  "max_iter" : args.max_iter,
                  "tol" : args.tol,
                  "hub" : args.hub,
                  "identifiers" : identifiers,
                  "residue_names" : residue_names}
        
        # Get dictionary of node+group and edge centrality values
        node_dict, edge_dict = get_centrality_dict(cent_list = centrality_names,
                                                   function_map = function_map, 
                                                   graph = graph,
                                                   **kwargs)

        # Dictionary is not empty so node centralities have been requested
        if len(node_dict) > 1:
            # Save dictionary as table
            write_table(fname = args.c_out,
                        centrality_dict = node_dict,
                        sort_by = args.sort_node)

            # Write PDB files if request (and if reference provided)
            if args.save_pdb and args.pdb is not None:
                write_pdb_files(centrality_dict = node_dict,
                                pdb = args.pdb,
                                fname = args.c_out)
            elif args.pdb is None:
                # Warn if no PDB provided
                warn_str = "No reference PDB file provided, no PDB files will "\
                           "be created."
                log.warning(warn_str)

        # Dictionary is not empty so edge centralities have been requested
        if edge_dict:
            write_table(fname = f"{args.c_out}_edge",
                             centrality_dict = edge_dict, 
                             sort_by = args.sort_edge)
            if args.save_mat:
                save_matrix(centrality_dict = edge_dict, 
                            identifiers = identifiers)

if __name__ == "__main__":
    main()
