from ast import keyword
from cmath import exp
import numpy as np
from bitarray import bitarray
from copy import deepcopy
import math
import base64
import io
import json
import pandas as pd
import random
import tracemalloc
import re
from enum import Enum
import string
import scipy
import sklearn
import nltk
import plotly.express as px
from nltk.stem import PorterStemmer
#nltk.download('stopwords')
#from nltk.corpus import stopwords
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import TruncatedSVD
from scipy.sparse import csc_matrix
import umap.umap_ as umap
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans
import hdbscan
from sklearn.neighbors import kneighbors_graph
import leidenalg
import igraph as ig

# Ignore warnings
import warnings

#from pyparsing import null_debug_action

#from formatter import NullFormatter
warnings.filterwarnings("ignore")


# this function reads in the data (copied from online)
def parse_data(filename):
    path = './' + filename
    try:
        if "csv" in filename:
            # Assume that the user uploaded a CSV or TXT file
            df = pd.read_csv(path, encoding = "utf-8", index_col=[0])
        elif "xls" in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(path, index_col=[0])
        elif "txt" or "tsv" in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_csv(path, delimiter = "\t",encoding = "ISO-8859-1",  index_col=[0])
    except Exception as e:
        print(e)
        return
    return df

def preProcessingFcn(tweet, removeWords=list(), stem=True, removeURL=True, removeStopwords=True, 
    removeNumbers=False, removePunctuation=True):
    """
    Cleans tweets by removing words, stemming, etc.
    """
    ps = PorterStemmer()
    tweet = tweet.lower()
    tweet = re.sub(r"\\n", " ", tweet)
    tweet = re.sub(r"&amp", " ", tweet)
    if removeURL==True:
        tweet = re.sub(r"http\S+", " ", tweet)
    if removeNumbers==True:
        tweet=  ''.join(i for i in tweet if not i.isdigit())
    if removePunctuation==True:
        for punct in string.punctuation:
            tweet = tweet.replace(punct, ' ')
    #if removeStopwords==True:
        #tweet = ' '.join([word for word in tweet.split() if word not in stopwords.words('english')])
    if len(removeWords)>0:
        tweet = ' '.join([word for word in tweet.split() if word not in removeWords])
    if stem==True:
        tweet = ' '.join([ps.stem(word) for word in tweet.split()])
    return tweet

class Operation:
    parents = []
    outputs = []
    operationType = ""
    parmeters = ""

    def __init__(self, inputArr, outputArr, searchType, parameter):
        self.parents = inputArr
        self.outputs = outputArr
        self.operationType = searchType
        self.parameters = parameter

class Subset:
    indices = bitarray()
    size = 0
    parent = None
    children = []
    def __init__(self, ind: bitarray):
        self.indices = ind

class Session:
    base = None
    currentSet = None
    length = 0
    def __init__(self, baseSet):
        self.length = len(baseSet)
        arr = bitarray(self.length)
        arr.setall(1)
        self.base = Subset(arr)
        self.base.size = self.length
        self.currentSet = self.base

    def makeOperation(self, outPut, count: int, funcName, params, input = None):
        if input == None:
            input = self.currentSet
        newSet = Subset(outPut)
        newSet.size = count
        newOp = Operation([input], [newSet], funcName, params)
        newOp.outputs[0].parent = newOp
        #input.children.append(deepcopy(newOp))
        #can't use append
        newOp.parents[0].children = newOp.parents[0].children + [newOp]
        self.currentSet = newSet

    def printColumn(self, column: int):
        for i in range(self.length):
            if (self.currentSet.indices[i]):
                print(retrieveRow(i)[column])

    def getCurrentSubset(self):
        s = []
        for i in range(self.length):
            if (self.currentSet.indices[i]):
                s.append(retrieveRow(i))
        return s

    def printCurrSubset(self, verbose: bool = False):
        for i in range(self.length):
            if (self.currentSet.indices[i]):
                if verbose:
                    print(retrieveRow(i))
                else:
                    print(i, ": ", retrieveRow(i)[15])

    def invert(self, input: bitarray):
        for i in range(len(input)):
            if input[i]:
                input[i] = False
            else:
                input[i] = True
        return input

    def randomSubset(self, probability, inputSet: Subset = None):
        if (inputSet == None):
            inputSet = self.currentSet
        random.seed()
        ans = bitarray(self.length)
        ans.setall(0)
        count = 0
        for i in range(self.length):
            if (inputSet.indices[i] and random.random() < probability):
                ans[i] = True
                count += 1
        self.makeOperation(ans, count, "randomSubset", "None")

    def simpleRandomSample(self, size: int, inputSet: Subset = None):
        if (inputSet == None):
            inputSet = self.currentSet
        random.seed()
        ans = bitarray(self.length)
        ans.setall(0)
        if(inputSet.size < size):
            # print("Invalid sample size")
            raise ValueError
        population = []
        for i in range(self.length):
            if inputSet.indices[i]:
                population.append(i)
        temp = np.random.choice(population, size, replace=False)
        for j in temp:
            ans[j] = True
        self.makeOperation(ans, size, "simpleRandomSample", size)

    def weightedSample(self, size: int, colName: str, inputSet: Subset = None):
        if (inputSet == None):
            inputSet = self.currentSet
        random.seed()
        ans = bitarray(self.length)
        ans.setall(0)
        if(inputSet.size < size):
            # print("Invalid sample size")
            raise ValueError
        population = []
        weights = []
        sum = 0
        for i in range(self.length):
            if inputSet.indices[i]:
                population.append(i)
                value = retrieveRow(i)[headerDict[colName]]
                if value != value : # still need to check if the colName corresponds with a number that can be weighted
                    value = 0
                value += 1
                sum += value
                weights.append(int(value))
        for j in range(len(weights)):
            weights[j] = float(weights[j] / sum)  
        temp = np.random.choice(population, size, replace=False, p=weights)
        #temp.sort()
        #print(temp)
        for k in temp:
            ans[k] = True
            #print(retrieveRow(k)[headerDict[colName]], end=" ")
        #print()
        self.makeOperation(ans, size, "weightedSample", colName + str(size))

    def searchKeyword(self, keywords: list, orMode: bool = False, inputSet: Subset = None):
        if (inputSet == None):
            inputSet = self.currentSet
        ans = bitarray(self.length)
        ans.setall(0)
        count = 0
        for i in range(self.length):
            if(inputSet.indices[i]):
                if (orMode):
                    include = False
                    for j in keywords:
                        if (retrieveRow(i)[15].find(j) != -1):
                            include = True
                            break
                else:
                    include = True
                    for j in keywords:
                        if (retrieveRow(i)[15].find(j) == -1):
                            include = False
                            break
                if include:
                    ans[i] = True
                    count += 1
        self.makeOperation(ans, count, "searchKeyword", keywords)

    def advancedSearch(self, expression: str, inputSet: Subset = None):
        if (inputSet == None):
            inputSet = self.currentSet
        ans = bitarray(self.length)
        ans.setall(0)
        count = 0
        # split the expression into a list of operands and keywords
        #regex = '\s*\(|\)\s*|\s*and\s*|\s*or\s*|\s*not\s*'
        #keywords = list(filter(None, re.split(regex, expression)))
        keywords = re.findall("'[^']+'", expression)
        # loop through to evaluate the truth value of each keyword
        for i in range(self.length):
            if(inputSet.indices[i]):
                newExpression = expression
                for j in keywords:
                    if(retrieveRow(i)[15].find(j[1:-1]) > -1):
                        newExpression = newExpression.replace(j, " True")
                    else:
                        newExpression = newExpression.replace(j, " False")
                if(eval(newExpression)):
                    ans[i] = True
                    count += 1
        self.makeOperation(ans, count, "advancedSearch", expression)
        

    def regexSearch(self, expression: str, inputSet: Subset = None):
        if (inputSet == None):
            inputSet = self.currentSet
        ans = bitarray(self.length)
        ans.setall(0)
        count = 0
        for i in range(self.length):
            if(inputSet.indices[i]):
                if(re.findall(expression, retrieveRow(i)[15], re.M)):
                    ans[i] = True
                    count += 1
        self.makeOperation(ans, count, "regexSearch", expression)
    
    def filterBy(self, colName: str, value, inputSet: Subset = None):
        if (inputSet == None):
            inputSet = self.currentSet
        ans = bitarray(self.length)
        ans.setall(0)
        count = 0
        for i in range(self.length):
            if (inputSet.indices[i] and retrieveRow(i)[headerDict[colName]] == value):
                ans[i] = True
                count += 1
        self.makeOperation(ans, count, "filterBy", colName + " = " + value)

    def setDiff(self, setOne: Subset, setZero: Subset = None):
        if (setZero == None):
            setZero = self.currentSet
        ans = bitarray(self.length)
        ans.setall(0)
        count = 0
        for i in range(self.length):
            if (setZero.indices[i] and not setOne.indices[i]):
                ans[i] = True
                count += 1
        self.makeOperation(ans, count, "setDiff", setOne)

    def setUnion(self, setOne: Subset, setZero: Subset = None):
        if (setZero == None):
            setZero = self.currentSet
        ans = bitarray(self.length)
        ans.setall(0)
        count = 0
        for i in range(self.length):
            if (setZero.indices[i] or setOne.indices[i]):
                ans[i] = True
                count += 1
        self.makeOperation(ans, count, "setUnion", setOne)

    def setIntersect(self, setOne: Subset, setZero: Subset = None):
        if (setZero == None):
            setZero = self.currentSet
        ans = bitarray(self.length)
        ans.setall(0)
        count = 0
        for i in range(self.length):
            if (setZero.indices[i] and setOne.indices[i]):
                ans[i] = True
                count += 1
        self.makeOperation(ans, count, "setintersect", setOne)

    def back(self, index: int = 0):
        if(self.currentSet.size == self.length) or index >= len(self.currentSet.parent.parents):
        # if(self.currentSet == self.base):
            # print("Can't go back")
            raise IndexError
        self.currentSet = self.currentSet.parent.parents[index]
    
    def next(self, index = -1):
        if len(self.currentSet.children) == 0 or index >= len(self.currentSet.children):
            # print("Can't go next")
            raise IndexError
        self.currentSet = self.currentSet.children[index].outputs[0]

    def printChildren(self):
        if len(self.currentSet.children) == 0:
            print("No children searches")
            return
        for i in self.currentSet.children:
            print("Type = ", i.operationType, " parameters = ", i.parameters)
    
    ##### Clustering ######
    
    # functions for dimension reduction: PCA and UMAP
    def dimred_PCA(self, docWordMatrix, ndims=25):
        tsvd = TruncatedSVD(n_components=ndims)
        tsvd.fit(docWordMatrix)
        docWordMatrix_pca = tsvd.transform(docWordMatrix)
        return docWordMatrix_pca

    def dimred_UMAP(self, matrix, ndims=2, n_neighbors=15):
        umap_2d = umap.UMAP(n_components=ndims, random_state=42, n_neighbors=n_neighbors, min_dist=0.0)
        proj_2d = umap_2d.fit_transform(matrix)
        #proj_2d = umap_2d.fit(matrix)
        return proj_2d

    # functions for clustering
    # HDBSCAN
    def cluster_hdbscan(self, points, min_obs):
        hdbscan_fcn = hdbscan.HDBSCAN(min_samples=10, min_cluster_size=min_obs)
        clusters = hdbscan_fcn.fit_predict(points).astype(str)
        return clusters

    # Gaussian Mixure Models
    def cluster_gmm(self, points, num_clusters):
        gmm_fcn = GaussianMixture(n_components=num_clusters, random_state=42).fit(points)
        clusters = gmm_fcn.predict(points).astype(str)
        return clusters

    # K-Means
    def cluster_kmeans(self, points, num_clusters):
        kmean_fcn = KMeans(init='random', n_clusters=num_clusters, random_state=42)
        clusters = kmean_fcn.fit(points).labels_.astype(str)
        return clusters


    def cluster_polis_leiden(self, points, num_neighbors):
        A = kneighbors_graph(points, num_neighbors, mode="connectivity", metric="euclidean", 
        p=2, metric_params=None, include_self=True, n_jobs=None)

        sources, targets = A.nonzero()
        weights = A[sources, targets]
        if isinstance(weights, np.matrix): # ravel data
            weights = weights.A1

        g = ig.Graph(directed=False)
        g.add_vertices(A.shape[0])  # each observation is a node
        edges = list(zip(sources, targets))
        g.add_edges(edges)
        g.es['weight'] = weights
        weights = np.array(g.es["weight"]).astype(np.float64)

        part = leidenalg.find_partition(
            g, 
            leidenalg.ModularityVertexPartition
        );

        leidenClusters = np.array(part.membership).astype(str)
        leidenClustersStr = [str(i) for i in leidenClusters]
    
        return leidenClusters

    def make_full_docWordMatrix(self, min_df = 5, inputSet: Subset = None):
        if (inputSet == None):
            inputSet = self.currentSet
        if inputSet.size == 0:
            return
        cleanedTweets = []
        for i in range(self.length):
            if inputSet.indices[i]:
                cleanedTweets.append(preProcessingFcn(retrieveRow(i)[15]))

        # create document-word matrix
        vectorizer = CountVectorizer(strip_accents='unicode', min_df= min_df, binary=False)
        docWordMatrix_orig = vectorizer.fit_transform(cleanedTweets)
        docWordMatrix_orig = docWordMatrix_orig.astype(dtype='float64')
        return docWordMatrix_orig, vectorizer.get_feature_names()
        #return docWordMatrix_orig.tolil(), vectorizer.get_feature_names()


    def dimRed_and_clustering(self, docWordMatrix_orig, 
    dimRed1_method, dimRed1_dims, clustering_when, clustering_method1, 
    num_clusters, min_obs, num_neighbors, dimRed2_method = None, inputSet = None):
        if (inputSet == None):
            inputSet = self.currentSet
        # read in document-word matrix
        # data = docWordMatrix_orig.data
        # rows, cols = docWordMatrix_orig.nonzero()
        # dims = docWordMatrix_orig.shape   
        # docWordMatrix = csc_matrix((data, (rows, cols)), shape=(dims[0], dims[1]))
        docWordMatrix = docWordMatrix_orig.tocsc()

        # do stage 1 dimension reduction
        if dimRed1_method == 'pca':
            dimRed1 = self.dimred_PCA(docWordMatrix, docWordMatrix_orig.shape[1])
        elif dimRed1_method == 'umap':
            #dimRed1 = self.dimred_UMAP(docWordMatrix, docWordMatrix_orig.shape[1])
            dimRed1 = self.dimred_UMAP(docWordMatrix, dimRed1_dims)
        else:
            raise ValueError("Dimension reduction method can be either 'pca' or 'umap'")
        # do stage 2 dimension reduction (if any)
        if dimRed1_dims > 2:
            if dimRed2_method == 'pca':
                dimRed2 = self.dimred_PCA(dimRed1, ndims=2)
            elif dimRed2_method == 'umap':
                dimRed2 = self.dimred_UMAP(dimRed1, ndims=2)
            else:
                raise ValueError("Dimension reduction method can be either 'pca' or 'umap'")
        else:
            dimRed2 = dimRed1
        # Clustering
        # get matrix at proper stage
        if clustering_when == 'before_stage1':
            clustering_data = docWordMatrix
        elif clustering_when == 'btwn':
            clustering_data = dimRed1
        elif clustering_when == 'after_stage2':
            clustering_data = dimRed2
        else: # also have to check if 'after_stage2' is used only when there is a stage 2
            raise ValueError("clustering_when should be in [before_stage1, btwn, after_stage2]")
        # perform clustering
        # rename clustering_method1 later
        if clustering_method1 == 'gmm':
            if clustering_when == 'before_stage1':
                clustering_data = clustering_data.toarray()
            clusters = self.cluster_gmm(clustering_data, num_clusters=num_clusters)
        elif clustering_method1 == 'k-means':
            clusters = self.cluster_kmeans(clustering_data, num_clusters=num_clusters)
        elif clustering_method1 == 'hdbscan':
            clusters = self.cluster_hdbscan(clustering_data, min_obs=min_obs)
        elif clustering_method1 == 'leiden':
            clusters = self.cluster_polis_leiden(clustering_data, num_neighbors=num_neighbors)
        else:
            raise ValueError("Clustering method must be in the list [gmm, k-means, hdbscan, leiden]")

        dimRed_cluster_plot = px.scatter(x= dimRed2[:,0], y= dimRed2[:,1], color= clusters)
        #dimRed_cluster_plot.show()
        # dimRed_cluster_plot.update_layout(clickmode='event+select')
        return dimRed_cluster_plot

# dataSet = None
# headers = None
# headerDict = dict()

def retrieveRow(rowNum: int):
    return dataSet[rowNum]

# def retrieveRow(rowNum: int):
#     return dataSet.iloc[rowNum].values

def createSession(fileName: str) -> Session:
    data = parse_data("allCensus_sample.csv")
    global dataSet 
    global headers
    global headerDict
    dataSet = data.values
    #dataSet = data
    headers = data.columns
    headerDict = dict()
    for i in range(len(headers)):
        colName = headers[i]
        headerDict[colName] = i
    s = Session(dataSet)
    return s

def test1():
    s = createSession("allCensus_sample.csv")
    s.advancedSearch("'covid' and ('hospital' or 'vaccine')")
    #s.printCurrSubset()
    print(s.currentSet.size)
    s.back()
    s.filterBy("State", "California")
    print(s.currentSet.size)
    s.advancedSearch("('hospital' or 'vaccine') and not 'Trump'")
    print(s.currentSet.size)
    s.back()

    s.advancedSearch("'trump' and not 'Trump'")
    print(s.currentSet.size)
    #s.printCurrSubset()
    s.back()
    s.regexSearch("trump")
    print(s.currentSet.size)

def test2():
    s = createSession("allCensus_sample.csv")
    s.randomSubset(0.01)
    print(s.currentSet.size)
    s.back()
    print(s.currentSet.size)
    s.back()
    s.next()
    print(s.currentSet.size)
    s.searchKeyword(["the"])
    print(s.currentSet.size)
    s.back()
    s.back()
    s.filterBy("State", "California")
    print(s.currentSet.size)
    s.back()
    s.advancedSearch("'trump' and not 'Trump'")
    print(s.currentSet.size)
    s.back()
    s.back()
    s.printChildren()
    s.next(0)
    print(s.currentSet.size)
    s.next(0)
    print(s.currentSet.size)
    s.next()

def test3():
    s = createSession("allCensus_sample.csv")
    s.randomSubset(0.001)
    print(s.currentSet.size)
    tempSet = s.currentSet
    s.back()
    print(tempSet.size)
    print(s.currentSet.size)
    s.advancedSearch("'the'", tempSet)
    print(s.currentSet.size)
    #s.printCurrSubset()
    s.searchKeyword(["the"], tempSet)
    print(s.currentSet.size)

def test4():
    s = createSession("allCensus_sample.csv")
    s.searchKeyword(["the", "Census"])
    print(s.currentSet.size)
    s.back()
    s.advancedSearch("'the' and 'Census'")
    print(s.currentSet.size)
    s.back()
    s.regexSearch("trump|Trump")
    print(s.currentSet.size)
    s.back()
    s.searchKeyword(["trump", "Trump"], True)
    print(s.currentSet.size)
    s.back()
    s.advancedSearch("'trump' or 'Trump'")
    print(s.currentSet.size)
    s.regexSearch("^[1-9]")
    #s.printCurrSubset()
    print(s.currentSet.size)
    s.back()
    s.back()
    s.advancedSearch("'(' and ')' and not ('{' or '}')")
    #s.printCurrSubset()
    print(s.currentSet.size)
    s.back()
    s.regexSearch("\(.*\)")
    print(s.currentSet.size)
    temp = s.currentSet
    s.back()
    s.advancedSearch(" '(' and ')' ")
    print(s.currentSet.size)
    s.setDiff(temp)
    #s.printCurrSubset()
    print(s.currentSet.size)
    
def test5():
    s = createSession("allCensus_sample.csv")
    s.simpleRandomSample(17000)
    #s.printCurrSubset()
    print(s.currentSet.size)
    s.back()
    s.weightedSample(10, "Retweets")
    #s.printCurrSubset()
    print(s.currentSet.size)

def test6():
    s = createSession("allCensus_sample.csv")
    s.simpleRandomSample(30)
    s.printCurrSubset()
    print("\n\n ---------------------------------------------------------- \n")
    temp = s.getCurrentSubset()
    print(temp)

def test7(): #same as test 1
    s = createSession("allCensus_sample.csv")
    print(type(dataSet))
    s.advancedSearch("'covid' and ('hospital' or 'vaccine')")
    #s.printCurrSubset()
    print(s.currentSet.size)
    s.back()
    s.filterBy("State", "California")
    print(s.currentSet.size)
    s.advancedSearch("('hospital' or 'vaccine') and not 'Trump'")
    print(s.currentSet.size)
    s.back()

    s.advancedSearch("'trump' and not 'Trump'")
    print(s.currentSet.size)
    #s.printCurrSubset()
    s.back()
    s.back()
    s.back()
    s.regexSearch("trump")
    print(s.currentSet.size)

def test8():
    s = createSession("allCensus_sample.csv")
    s.filterBy("State", "New Jersey")
    s.regexSearch("Trump")
    print(s.currentSet.size)
    #s.printCurrSubset()
    matrix, words = s.make_full_docWordMatrix(min_df= 1)
    #print(words)
    #print(matrix)
    test = s.dimRed_and_clustering(matrix, 'pca', 2, 'umap', 'after_stage2', 'gmm', 25, 2, 25)
    print(test)
    #print(matrix)

def test9():
    s = createSession("allCensus_sample.csv")
    s.simpleRandomSample(10)
    print(s.currentSet.size)
    s.simpleRandomSample(4)
    print(s.currentSet.size)

def test10():
    s = createSession("allCensus_sample.csv")
    s.simpleRandomSample(30)
    matrix, words = s.make_full_docWordMatrix(3)
    test = s.dimRed_and_clustering(matrix, dimRed1_method= 'pca', dimRed1_dims=2, clustering_when='before_stage1', 
        clustering_method1='leiden', num_clusters=2, min_obs= 2, num_neighbors=2)
    print(test)
if __name__=='__main__':
    # test = parse_data("allCensus_sample.csv")
    # dataSet = test.values
    # headers = test.columns
    # for i in range(len(headers)):
    #     colName = headers[i]
    #     headerDict[colName] = i
    test10()
