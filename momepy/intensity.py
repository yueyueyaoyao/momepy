#!/usr/bin/env python
# -*- coding: utf-8 -*-

# intensity.py
# definitons of intensity characters

from tqdm import tqdm  # progress bar
import pandas as pd
import numpy as np
import collections


class AreaRatio:
    """
    Calculate covered area ratio or floor area ratio of objects.

    Either unique_id or left_unique_id and right_unique_id are required.

    .. math::
        \\textit{covering object area} \\over \\textit{covered object area}

    Parameters
    ----------
    left : GeoDataFrame
        GeoDataFrame containing objects being covered (e.g. land unit)
    right : GeoDataFrame
        GeoDataFrame with covering objects (e.g. building)
    left_areas : str, list, np.array, pd.Series
        the name of the left dataframe column, np.array, or pd.Series where is stored area value.
    right_areas : str, list, np.array, pd.Series
        the name of the right dataframe column, np.array, or pd.Series where is stored area value
        representing either projected or floor area.
    unique_id : str (default None)
        name of the column with unique id shared amongst left and right gdfs.
        If there is none, it could be generated by :py:func:'momepy.unique_id()'.
    left_unique_id : str, list, np.array, pd.Series (default None)
        the name of the left dataframe column, np.array, or pd.Series where is stored shared unique ID
    right_unique_id : str, list, np.array, pd.Series (default None)
        the name of the left dataframe column, np.array, or pd.Series where is stored shared unique ID

    Attributes
    ----------
    ar : Series
        Series containing resulting values
    left : GeoDataFrame
        original left GeoDataFrame
    right : GeoDataFrame
        original right GeoDataFrame
    left_areas :  Series
        Series containing used left areas
    right_areas :  Series
        Series containing used right areas
    left_unique_id : Series
        Series containing used left ID
    right_unique_id : Series
        Series containing used right ID

    References
    ---------
    Schirmer PM and Axhausen KW (2015) A multiscale classiﬁcation of urban morphology.
    Journal of Transport and Land Use 9(1): 101–130.

    Examples
    --------
    >>> tessellation_df['CAR'] = mm.AreaRatio(tessellation_df, buildings_df, 'area', 'area', 'uID').ar
    """

    def __init__(
        self,
        left,
        right,
        left_areas,
        right_areas,
        unique_id=None,
        left_unique_id=None,
        right_unique_id=None,
    ):
        self.left = left
        self.right = right

        left = left.copy()
        right = right.copy()

        if unique_id:
            left_unique_id = unique_id
            right_unique_id = unique_id
        else:
            if left_unique_id is None or right_unique_id is None:
                raise ValueError(
                    "Unique ID not correctly set. Use either network_id or both"
                    "left_unique_id and right_unique_id."
                )
        self.left_unique_id = left_unique_id
        self.right_unique_id = right_unique_id

        if not isinstance(left_areas, str):
            left["mm_a"] = left_areas
            left_areas = "mm_a"
        self.left_areas = left[left_areas]
        if not isinstance(right_areas, str):
            right["mm_a"] = right_areas
            right_areas = "mm_a"
        self.right_areas = right[right_areas]

        look_for = right[
            [right_unique_id, right_areas]
        ]  # keeping only necessary columns
        look_for.rename(index=str, columns={right_areas: "lf_area"}, inplace=True)
        objects_merged = left[[left_unique_id, left_areas]].merge(
            look_for, left_on=left_unique_id, right_on=right_unique_id
        )

        self.ar = objects_merged["lf_area"] / objects_merged[left_areas]


class Count:
    """
    Calculate the number of elements within an aggregated structure.

    Aggregated structure can be typically block, street segment or street node (their snapepd objects). Right gdf has to have
    unique id of aggregated structure assigned before hand (e.g. using :py:func:`momepy.get_network_id`).
    If weighted=True, number of elements will be divided by the area of lenght (based on geometry type) of aggregated
    element, to return relative value.

    .. math::
        \\sum_{i \\in aggr} (n_i);\\space \\frac{\\sum_{i \\in aggr} (n_i)}{area_{aggr}}

    Parameters
    ----------
    left : GeoDataFrame
        GeoDataFrame containing aggregation to analyse
    right : GeoDataFrame
        GeoDataFrame containing objects to analyse
    left_id : str
        name of the column where is stored unique ID in left gdf
    right_id : str
        name of the column where is stored unique ID of aggregation in right gdf
    weighted : bool (default False)
        if weighted=True, count will be divided by the area or length

    Attributes
    ----------
    c : Series
        Series containing resulting values
    left : GeoDataFrame
        original left GeoDataFrame
    right : GeoDataFrame
        original right GeoDataFrame
    left_id : Series
        Series containing used left ID
    right_id : Series
        Series containing used right ID
    weighted : bool
        used weighted value

    References
    ----------
    1. Hermosilla T, Ruiz LA, Recio JA, et al. (2012) Assessing contextual descriptive features
    for plot-based classification of urban areas. Landscape and Urban Planning, Elsevier B.V.
    106(1): 124–137.
    2. Feliciotti A (2018) RESILIENCE AND URBAN DESIGN:A SYSTEMS APPROACH TO THE
    STUDY OF RESILIENCE IN URBAN FORM. LEARNING FROM THE CASE OF GORBALS. Glasgow.

    Examples
    --------
    >>> blocks_df['buildings_count'] = mm.Count(blocks_df, buildings_df, 'bID', 'bID', weighted=True).c
    """

    def __init__(self, left, right, left_id, right_id, weighted=False):
        self.left = left
        self.right = right
        self.left_id = left[left_id]
        self.right_id = right[right_id]
        self.weighted = weighted

        count = collections.Counter(right[right_id])
        df = pd.DataFrame.from_dict(count, orient="index", columns=["mm_count"])
        joined = left[[left_id, "geometry"]].join(df["mm_count"], on=left_id)
        joined.loc[joined["mm_count"].isna(), "mm_count"] = 0

        if weighted:
            if left.geometry[0].type in ["Polygon", "MultiPolygon"]:
                joined["mm_count"] = joined["mm_count"] / left.geometry.area
            elif left.geometry[0].type in ["LineString", "MultiLineString"]:
                joined["mm_count"] = joined["mm_count"] / left.geometry.length
            else:
                raise TypeError("Geometry type does not support weighting.")

        self.c = joined["mm_count"]


class Courtyards:
    """
    Calculate the number of courtyards within the joined structure.

    Parameters
    ----------
    gdf : GeoDataFrame
        GeoDataFrame containing objects to analyse
    block_id : str, list, np.array, pd.Series
        the name of the dataframe column, np.array, or pd.Series where is stored block ID
    spatial_weights : libpysal.weights, optional
        spatial weights matrix - If None, Queen contiguity matrix will be calculated
        based on objects. It is to denote adjacent buildings (note: based on index).

    Attributes
    ----------
    c : Series
        Series containing resulting values
    gdf : GeoDataFrame
        original GeoDataFrame
    block_id : Series
        Series containing used block ID
    sw : libpysal.weights
        spatial weights matrix

    References
    ---------
    Schirmer PM and Axhausen KW (2015) A multiscale classiﬁcation of urban morphology.
    Journal of Transport and Land Use 9(1): 101–130.

    Examples
    --------
    >>> buildings_df['courtyards'] = mm.Courtyards(buildings_df, 'bID').c
    Calculating spatial weights...
    """

    def __init__(self, gdf, block_id, spatial_weights=None):
        self.gdf = gdf

        results_list = []
        gdf = gdf.copy()

        if not isinstance(block_id, str):
            gdf["mm_bid"] = block_id
            block_id = "mm_bid"

        self.block_id = gdf[block_id]
        # if weights matrix is not passed, generate it from objects
        if spatial_weights is None:
            print("Calculating spatial weights...")
            from libpysal.weights import Queen

            spatial_weights = Queen.from_dataframe(gdf, silence_warnings=True)

        self.sw = spatial_weights
        # dict to store nr of courtyards for each uID
        courtyards = {}
        components = pd.Series(spatial_weights.component_labels, index=gdf.index)
        for index, row in tqdm(gdf.iterrows(), total=gdf.shape[0]):
            # if the id is already present in courtyards, continue (avoid repetition)
            if index in courtyards:
                continue
            else:
                comp = spatial_weights.component_labels[index]
                to_join = components[components == comp].index
                joined = gdf.loc[to_join]
                dissolved = joined.geometry.buffer(
                    0.01
                ).unary_union  # buffer to avoid multipolygons where buildings touch by corners only
                try:
                    interiors = len(list(dissolved.interiors))
                except (ValueError):
                    print("Something unexpected happened.")
                for b in to_join:
                    courtyards[b] = interiors  # fill dict with values
        # copy values from dict to gdf
        for index, row in tqdm(gdf.iterrows(), total=gdf.shape[0]):
            results_list.append(courtyards[index])

        self.c = pd.Series(results_list, index=gdf.index)


class BlocksCount:
    """
    Calculates the weighted number of blocks

    Number of blocks within `k` topological steps defined in spatial_weights.

    .. math::


    Parameters
    ----------
    gdf : GeoDataFrame
        GeoDataFrame containing morphological tessellation
    block_id : str, list, np.array, pd.Series
        the name of the objects dataframe column, np.array, or pd.Series where is stored block ID.
    spatial_weights : libpysal.weights
        spatial weights matrix
    unique_id : str
        name of the column with unique id used as spatial_weights index
    weigted : bool, default True
        return value weighted by the analysed area (True) or pure count (False)

    Attributes
    ----------
    bc : Series
        Series containing resulting values
    gdf : GeoDataFrame
        original GeoDataFrame
    block_id : Series
        Series containing used block ID
    sw : libpysal.weights
        spatial weights matrix
    id : Series
        Series containing used unique ID
    weighted : bool
        used weighted value

    References
    ----------
    Dibble J, Prelorendjos A, Romice O, et al. (2017) On the origin of spaces: Morphometric foundations of urban form evolution.
    Environment and Planning B: Urban Analytics and City Science 46(4): 707–730.

    Examples
    --------
    >>> sw4 = mm.sw_high(k=4, gdf='tessellation_df', ids='uID')
    >>> tessellation_df['blocks_within_4'] = mm.BlocksCount(tessellation_df, 'bID', sw4, 'uID').bc
    """

    def __init__(self, gdf, block_id, spatial_weights, unique_id, weighted=True):

        self.gdf = gdf
        self.sw = spatial_weights
        self.id = gdf[unique_id]
        self.weighted = weighted

        # define empty list for results
        results_list = []
        data = gdf.copy()
        if not isinstance(block_id, str):
            data["mm_bid"] = block_id
            block_id = "mm_bid"
        self.block_id = data[block_id]
        data = data.set_index(unique_id)

        for index, row in tqdm(data.iterrows(), total=data.shape[0]):
            neighbours = spatial_weights.neighbors[index].copy()
            if neighbours:
                neighbours.append(index)
            else:
                neighbours = row[unique_id]
            vicinity = data.loc[neighbours]

            if weighted is True:
                results_list.append(
                    len(set(list(vicinity[block_id]))) / sum(vicinity.geometry.area)
                )
            elif weighted is False:
                results_list.append(len(set(list(vicinity[block_id]))))
            else:
                raise ValueError("Attribute 'weighted' needs to be True or False.")

        self.bc = pd.Series(results_list, index=gdf.index)


class Reached:
    """
    Calculates the number of objects reached within topological steps on street network

    Number of elements within topological steps defined in spatial_weights. If
    spatial_weights are None, it will assume topological distance 0 (element itself).
    If mode='area', returns sum of areas of reached elements. Requires unique_id
    of network assigned beforehand (e.g. using :py:func:`momepy.get_network_id`).

    .. math::


    Parameters
    ----------
    left : GeoDataFrame
        GeoDataFrame containing streets (either segments or nodes)
    right : GeoDataFrame
        GeoDataFrame containing elements to be counted
    left_id : str, list, np.array, pd.Series (default None)
        the name of the left dataframe column, np.array, or pd.Series where is
        stored ID of streets (segments or nodes).
    right_id : str, list, np.array, pd.Series (default None)
        the name of the right dataframe column, np.array, or pd.Series where is
        stored ID of streets (segments or nodes).
    spatial_weights : libpysal.weights (default None)
        spatial weights matrix
    mode : str (default 'count')
        mode of calculation. If ``'count'`` function will return the count of reached elements.
        If ``'sum'``, it will return sum of ``'values'``. If ``'mean'`` it will return mean value
        of `'`values'``. If `'std'` it will return standard deviation
        of ``'values'``. If ``'values'`` not set it will use of areas
        of reached elements.
    values : str (default None)
        the name of the objects dataframe column with values used for calculations

    Attributes
    ----------
    r : Series
        Series containing resulting values
    left : GeoDataFrame
        original left GeoDataFrame
    right : GeoDataFrame
        original right GeoDataFrame
    left_id : Series
        Series containing used left ID
    right_id : Series
        Series containing used right ID
    mode : str
        mode of calculation
    sw : libpysal.weights
        spatial weights matrix (if set)

    Examples
    --------
    >>> streets_df['reached_buildings'] = mm.Reached(streets_df, buildings_df, 'uID').r

    """

    def __init__(
        self,
        left,
        right,
        left_id,
        right_id,
        spatial_weights=None,
        mode="count",
        values=None,
    ):
        self.left = left
        self.right = right
        self.sw = spatial_weights
        self.mode = mode

        # define empty list for results
        results_list = []

        if not isinstance(right_id, str):
            right = right.copy()
            right["mm_id"] = right_id
            right_id = "mm_id"
        self.right_id = right[right_id]
        if not isinstance(left_id, str):
            left = left.copy()
            left["mm_lid"] = left_id
            left_id = "mm_lid"
        self.left_id = left[left_id]
        if mode == "count":
            count = collections.Counter(right[right_id])

        # iterating over rows one by one
        for index, row in tqdm(left.iterrows(), total=left.shape[0]):
            if spatial_weights is None:
                ids = [row[left_id]]
            else:
                neighbours = list(spatial_weights.neighbors[index])
                neighbours.append(index)
                ids = left.iloc[neighbours][left_id]
            if mode == "count":
                counts = []
                for nid in ids:
                    counts.append(count[nid])
                results_list.append(sum(counts))
            elif mode == "sum":
                if values:
                    results_list.append(
                        sum(right.loc[right[right_id].isin(ids)][values])
                    )
                else:
                    results_list.append(
                        sum(right.loc[right[right_id].isin(ids)].geometry.area)
                    )
            elif mode == "mean":
                if values:
                    results_list.append(
                        np.nanmean(right.loc[right[right_id].isin(ids)][values])
                    )
                else:
                    results_list.append(
                        np.nanmean(right.loc[right[right_id].isin(ids)].geometry.area)
                    )
            elif mode == "std":
                if values:
                    results_list.append(
                        np.nanstd(right.loc[right[right_id].isin(ids)][values])
                    )
                else:
                    results_list.append(
                        np.nanstd(right.loc[right[right_id].isin(ids)].geometry.area)
                    )

        self.r = pd.Series(results_list, index=left.index)


class NodeDensity:
    """
    Calculate the density of nodes within topological steps on street network defined in spatial_weights.

    Calculated as number of nodes within k steps / cummulative length of street network within k steps.
    node_start and node_end is standard output of :py:func:`momepy.nx_to_gdf` and is compulsory.

    .. math::


    Parameters
    ----------
    left : GeoDataFrame
        GeoDataFrame containing nodes of street network
    right : GeoDataFrame
        GeoDataFrame containing edges of street network
    spatial_weights : libpysal.weights
        spatial weights matrix capturing relationship between nodes within set topological distance
    weighted : bool (default False)
        if True density will take into account node degree as k-1
    node_degree : str (optional)
        name of the column of left gdf containing node degree. Used if weighted=True
    node_start : str (default 'node_start')
        name of the column of right gdf containing id of starting node
    node_end : str (default 'node_end')
        name of the column of right gdf containing id of ending node

    Attributes
    ----------
    nd : Series
        Series containing resulting values
    left : GeoDataFrame
        original left GeoDataFrame
    right : GeoDataFrame
        original right GeoDataFrame
    node_start : Series
        Series containing used ids of starting node
    node_end : Series
        Series containing used ids of ending node
    sw : libpysal.weights
        spatial weights matrix
    weighted : bool
        used weighted value
    node_degree : Series
        Series containing used node degree values


    References
    ---------
    Dibble J, Prelorendjos A, Romice O, et al. (2017) On the origin of spaces: Morphometric foundations of urban form evolution.
    Environment and Planning B: Urban Analytics and City Science 46(4): 707–730.

    Examples
    --------
    >>> nodes['density'] = mm.NodeDensity(nodes, edges, sw).nd

    """

    def __init__(
        self,
        left,
        right,
        spatial_weights,
        weighted=False,
        node_degree=None,
        node_start="node_start",
        node_end="node_end",
    ):
        self.left = left
        self.right = right
        self.sw = spatial_weights
        self.weighted = weighted
        if weighted:
            self.node_degree = left[node_degree]
        self.node_start = right[node_start]
        self.node_end = right[node_end]
        # define empty list for results
        results_list = []

        # iterating over rows one by one
        for index, row in tqdm(left.iterrows(), total=left.shape[0]):

            neighbours = list(spatial_weights.neighbors[index])
            neighbours.append(index)
            if weighted:
                neighbour_nodes = left.iloc[neighbours]
                number_nodes = sum(neighbour_nodes[node_degree] - 1)
            else:
                number_nodes = len(neighbours)

            edg = right.loc[right["node_start"].isin(neighbours)].loc[
                right["node_end"].isin(neighbours)
            ]
            length = sum(edg.geometry.length)

            if length > 0:
                results_list.append(number_nodes / length)
            else:
                results_list.append(0)

        self.nd = pd.Series(results_list, index=left.index)


class Density:
    """
    Calculate the gross density

    .. math::


    Parameters
    ----------
    gdf : GeoDataFrame
        GeoDataFrame containing objects to analyse
    values : str, list, np.array, pd.Series
        the name of the dataframe column, np.array, or pd.Series where is stored character value.
    spatial_weights : libpysal.weight
        spatial weights matrix
    unique_id : str
        name of the column with unique id used as spatial_weights index
    areas :  str, list, np.array, pd.Series (optional)
        the name of the dataframe column, np.array, or pd.Series where is stored area value. If None,
        gdf.geometry.area will be used.

    Attributes
    ----------
    d : Series
        Series containing resulting values
    gdf : GeoDataFrame
        original GeoDataFrame
    values : Series
        Series containing used values
    sw : libpysal.weights
        spatial weights matrix
    id : Series
        Series containing used unique ID
    areas : Series
        Series containing used area values

    References
    ---------
    Dibble J, Prelorendjos A, Romice O, et al. (2017) On the origin of spaces: Morphometric foundations of urban form evolution.
    Environment and Planning B: Urban Analytics and City Science 46(4): 707–730.

    Examples
    --------
    >>> tessellation_df['floor_area_dens'] = mm.Density(tessellation_df, 'floor_area', sw, 'uID').d
    """

    def __init__(self, gdf, values, spatial_weights, unique_id, areas=None):
        self.gdf = gdf
        self.sw = spatial_weights
        self.id = gdf[unique_id]

        # define empty list for results
        results_list = []
        data = gdf.copy()

        if values is not None:
            if not isinstance(values, str):
                data["mm_v"] = values
                values = "mm_v"
        self.values = data[values]
        if areas is not None:
            if not isinstance(areas, str):
                data["mm_a"] = areas
                areas = "mm_a"
        else:
            data["mm_a"] = data.geometry.area
            areas = "mm_a"
        self.areas = data[areas]

        data = data.set_index(unique_id)
        # iterating over rows one by one
        for index, row in tqdm(data.iterrows(), total=data.shape[0]):
            neighbours = spatial_weights.neighbors[index].copy()
            if neighbours:
                neighbours.append(index)
            else:
                neighbours = index
            subset = data.loc[neighbours]
            values_list = subset[values]
            areas_list = subset[areas]

            results_list.append(sum(values_list) / sum(areas_list))

        self.d = pd.Series(results_list, index=gdf.index)
