import pandas as pd
import numpy as np
import json
import weka.core.jvm as jvm
from weka.core.converters import Loader, Saver
import os
import random
import math
import matplotlib as plt

np.set_printoptions(precision=10)
pd.set_option('display.precision',10)

try:
    with open("hac.cfg") as f:
        config = json.load(f)
    DPATH = config.get("data_path")
    DATASET = config.get("dataset")
except Exception as e:
    print(e)
    print("Make sure the config file data_path is setup.")


class Cluster(object):
    """Singular cluster."""
    values = pd.DataFrame([])
    
    def __init__(self, values, right_cluster=None, left_cluster=None):
        self.right = right_cluster
        self.left = left_cluster
        if type(values) != type(self.values):
            data = np.array([values.values])
            self.values = pd.DataFrame(data, columns=values.index.values, index=[values.name])
        else:
            self.values = values.copy()
        self.mean = self.values.mean()
        #self.values.append(values)
        #self.reevaluate_mean()

    def merge_clusters(self, y):
        old_left = self.left
        self.left = Cluster(self.values, 
                                    right_cluster=self.right, 
                                    left_cluster=old_left)
        self.right = y
    
        self.values = pd.concat([self.values, y.get_values()])
        #self.reevaluate_mean()
        self.mean = self.values.mean()

    def centroid(self):
        y = 0
        self.length = len(self.values)
        #for x in self.values:
            #if want to get the mean distance df.apply(distance)
            #print(self.values.mean())
        #self.mean_distance = y/len(self.values)

    def mean(self):
        return self.mean

    def get_values(self):
        return self.values

    def len(self):
        self.length = len(self.values)
        return self.length



class Buckshot(object):
    """Performs hierarchical clustering on randomly subset of data
    sqrt of n; n is the entire dataset.

    Uses ____ merging criteria. Measures quality with ____.

    Parameters
        k (int): Number of clusters.
    """

    data_name = 'adult-big'
    output = 'adult.out'
    continuous_cols =[]
    def __init__(self, k=10):
        self.dataset = DATASET
        self.k = k

    def run(self):
        self.preprocess()
        self.hac()

    def preprocess(self):
        self.load_df()
        del self.df['fnlwgt']
        self.replace_missing_values()
        self.normalize_data()
    
    #comparing two centroids for nominal attribute if different have a distance of 1
    def load_df(self):
        """Converts the dataset to pandas and numpy friendly file format."""
        if 'arff' in self.dataset:
            self.df = load_arff_to_df(self.dataset)
            self.df = self.df.rename(columns=lambda x: x.replace(':', ''))
            self.df = self.df.rename(columns=lambda x: x.replace('-', '_'))

    def replace_missing_values(self):
        """Replaces missing values with mean and mode."""

        for col in self.df.columns:
            current = self.df[col]
            if current.dtype == 'int64':
                current.fillna(current.mean(), inplace=True)
                self.continuous_cols.append(col)
            else:
                current.fillna(self.df[col].mode()[0], inplace=True)
            self.df[col] = current
    
    def normalize_data(self):
        """Normalizes all continuous values in dataFrame."""
        self.df['class'] = self.df['class'].apply(convert_class)
        int_df = self.df[self.continuous_cols]
        int_df = (int_df - int_df.mean()) / (int_df.max() - int_df.min())
        self.df[self.continuous_cols] = int_df

    def get_random_samples(self):
        """Creates random sampled dataframe equal to sqrt(n)."""
        n = len(self.df.index)
        sqrt_n = int(math.sqrt(n))
        rows = random.sample(self.df.index, sqrt_n)
        self.random = self.df.ix[rows]
        self.remaining = self.df.drop(rows)

    def hac(self):
        """Creates k clusters with randomly sqrt(n) samples."""
        self.get_random_samples()
        self.init_matrix()
        
        while(len(self.clusters) > self.k):
            #get index of the two clusters that are closest together
            minimum = np.where(self.matrix == self.matrix.min())[0]
            min_x = minimum[0]
            min_y = minimum[1]
            #remove cluster to be merged into clusters[min_x] 
            to_merge = self.clusters.pop(min_y)
            self.clusters[min_x].merge_clusters(to_merge)
            #right clusters should be smaller
            self.update_matrix()
    
    def init_matrix(self):
        n = len(self.random.index)
        matrix = np.empty(shape=[n,n])
        
        self.clusters = []
        index = range(0,n)
        for n1 in index:
            row1 = self.random.iloc[n1]
            current_cluster = Cluster(values=row1)
            #create a distance matrix
            for n2 in index:
                row2 = self.random.iloc[n2]
                dist = distance(row1,row2)
                matrix[n1][n2] = dist
            
            self.clusters.append(current_cluster)
        #minimums won't return self -> 0,0, 1,1, 2,2...
        np.fill_diagonal(matrix, np.inf)
        self.matrix = matrix
    
    def update_matrix(self):
        #create new distance matrix
        n = len(self.clusters)
        matrix = np.empty(shape=[n,n])
        print("Clusters: %s" % str(n))
        
        for cluster1 in self.clusters:
            r1 = cluster1.mean()
            i1 = self.clusters.index(cluster1)
            for cluster2 in self.clusters:
                r2 = cluster2.mean()
                i2 = self.clusters.index(cluster2)
                matrix[i1][i2] = distance(r1, r2)

        np.fill_diagonal(matrix, np.inf)
        del self.matrix
        self.matrix = matrix

    def k_means(self):

def convert_class(val):
    if val == '<=50K':
        return 0
    elif val == 'Male':
        return 0 
    else:
        return 1

    
def distance(x, y):
        """Measures distance of two matrices/vectors w/ euclidean dist."""
        dist = 0 
        for i in range(0,len(x)):
            j = x.iloc[i]
            k = y.iloc[i]
            if type(j) == str:
                if j == k:
                    k = 0
                    j = 0
                else:
                    j = 0
                    k = 1
            dist += (j-k)**2
            #time.sleep(.01)
        dist = math.sqrt(dist)
        #print(dist)
        return dist


def load_arff_to_df(filepath):
    """Loads arff into csv then pandas reads that into a dataframe.

    Returns:
        df (pandas.DataFrame): Loaded DataFrame from filepath
    """
    temp_csv = filepath[:-5] + '.csv'
    try:
        if os.path.isfile(temp_csv):
            raise BuckshotFileError("CSV exists. Skipping load_arff_to_df()")
        jvm.start(max_heap_size='512m')
        loader = Loader(classname="weka.core.converters.ArffLoader")
        data = loader.load_file(filepath)
        saver = Saver(classname="weka.core.converters.CSVSaver")
        saver.save_file(data, temp_csv)
        jvm.stop()
    except BuckshotFileError as e:
        #print(e)
        pass
    finally:
        df = pd.read_csv(temp_csv, na_values='?', float_precision=12)
        #convert all ints to floats 
        #os.remove(temp_csv)
        return df

    
class BuckshotFileError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return repr(self.msg)


if __name__ == '__main__':
    b = Buckshot()
    #ab.scipy_test()
    b.run()