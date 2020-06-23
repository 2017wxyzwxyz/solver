#!usr/bin/python 3.7
#-*-coding:utf-8-*-

'''
@file: same_size_kmeans.py, equal size clustering with heuristics
@Author: Jing Wang (jingw2@foxmail.com)
@Date: 06/16/2020
@paper: 
@github reference: 
@Web: https://elki-project.github.io/tutorial/same-size_k_means
'''

from scipy.spatial.distance import cdist
import numpy as np 
from scipy.linalg import norm
import base
from sklearn.cluster._k_means import _k_init # kmeans ++ 
from sklearn.preprocessing import OneHotEncoder
import collections

class SameSizeKMeans(base.Base):

    def __init__(self, n_clusters, max_iters=1000, distance_func=cdist, random_state=42):
        '''
        Args:
            n_clusters (int): number of clusters 
            max_iters (int): maximum iterations
            distance_func (object): callable function with input (X, centers) / None, by default is l2-distance
            random_state (int): random state to initiate, by default it is 42
        '''
        super(SameSizeKMeans, self).__init__(n_clusters, max_iters, distance_func)
        self.random_state = np.random.RandomState(random_state)
    
    def fit(self, X):
        '''
        Args:
            X (array like): shape (n_samples, n_features)
        '''
        n_samples, _ = X.shape
        minsize = n_samples // self.n_clusters
        maxsize = (n_samples + self.n_clusters - 1) // self.n_clusters

        # print("min size: ", minsize)
        # print("max size: ", maxsize)
        
        # initiate 
        labels = self.init(X)
        encoder = OneHotEncoder()
        labels_onehot = encoder.fit_transform(labels.reshape((-1, 1))).toarray()
        itr = 0
        clusters = collections.Counter(labels)
        while True:
            # update centers
            labels_onehot = encoder.fit_transform(labels.reshape((-1, 1))).toarray()
            centers = self.update_centers(X, labels_onehot)
            # compute distance to centers 
            dist_mat = self.distance_func(X, centers)
            # calculate preference
            labels = labels.astype(int)
            preference = dist_mat[range(n_samples), labels] - np.min(dist_mat, axis=1)
            argsort = np.argsort(preference)[::-1] # descending order
            # transfer list 
            transfer = {c: [] for c in range(self.n_clusters)}

            for sample_id in argsort:
                source = labels[sample_id]
                dest = np.argmin(dist_mat[sample_id])

                # cannot transfer to same cluster
                if source == dest:
                    continue

                sample_gain = dist_mat[sample_id][source] - dist_mat[sample_id][dest]

                # find if there is pair transfer
                dest_transfer = transfer[dest]
                gains = {}
                for other_id in dest_transfer:
                    other_gain = dist_mat[other_id][dest] - dist_mat[other_id][source]
                    gain = sample_gain + other_gain
                    if gain > 0:
                        gains[other_id] = gain
                if len(gains) > 0:
                    other_id = sorted(gains.items(), key=lambda x: x[1], reverse=True)[0][0]
                    labels[other_id], labels[sample_id] \
                        = labels[sample_id], labels[other_id]
                    transfer[dest].remove(other_id)
                    if sample_id in transfer[source]:
                        transfer[source].remove(sample_id)
                    continue
                
                # if cluster size allows, move a single object
                if (sample_gain > 0 and clusters[dest] < maxsize and clusters[source] > minsize):
                    labels[sample_id] = dest
                    clusters[dest] += 1 
                    clusters[source] -= 1
                    if sample_id in transfer[source]:
                        transfer[source].remove(sample_id)
                    continue
                
                # if the object would prefer a different cluster, put in transfer list
                if (sample_gain > 0):
                    transfer[source].append(sample_id)
                
            if len(transfer) <= 0:
                break 
                
            itr += 1 
            pending = sum([len(val) for key, val in transfer.items()])
            if itr >= self.max_iters:
                print("Reach maximum iterations! Now pending transfer samples {}!".format(pending))
                break 

        self.centers = centers 
        self.labels = labels    
    
    def predict(self, X):
        dist_mat = self.distance_func(X, self.centers)
        labels = np.argmin(dist_mat, axis=1)
        return labels
    
    def update_centers(self, X, labels):
        '''
        Update centers 
        Args:
            X (array like): (n_samples, n_features)
            labels (array like): (n_samples, n_clusters), one-hot array
        
        Return:
            centers (array like): (n_clusters, n_features)
        '''
        centers = (X.T.dot(labels)).T / np.sum(labels, axis=0).reshape((-1, 1))
        return centers

        
    def init(self, X):
        '''
        Initiate centroids based on X input with kmeans ++ 

        Args:
            X (array like): shape is (n_samples, n_features)
        
        Returns:
            labels (array like): shape is (n_samples,) 
        '''
        n_samples, n_features = X.shape
        max_size = (n_samples + self.n_clusters - 1) // self.n_clusters
        # initiate centroids with kmeans++
        X_squared_norm = np.sum(np.square(X), axis=1)
        centers = _k_init(X, self.n_clusters, X_squared_norm, self.random_state)
        
        # calculate priority 
        dist_mat = cdist(X, centers) # (n_samples, n_clusters)
        priority = np.max(dist_mat, axis=1) - np.min(dist_mat, axis=1)
        argsort = np.argsort(priority)[::-1] # descending order
        clusters = {i: 0 for i in range(self.n_clusters)}

        # assign to clusters based on priority
        samples = list(range(n_samples))
        visited = set()
        dist_mat_copy = dist_mat.copy()
        m = np.zeros_like(dist_mat_copy)
        labels = np.zeros(n_samples)
        while len(samples) > 0:
            for sample_id in argsort:
                if sample_id in visited:
                    continue
                cluster_id = np.argmin(dist_mat_copy[sample_id])
                if clusters[cluster_id] < max_size:
                    labels[sample_id] = cluster_id
                    clusters[cluster_id] += 1
                    samples.remove(sample_id)
                    visited.add(sample_id)
                else:
                    break 
            dist_mat_copy = dist_mat.copy()
            # mask full cluster column
            m[:, cluster_id] = 1
            dist_mat_copy = np.ma.masked_array(dist_mat_copy, m)
            priority = np.max(dist_mat_copy, axis=1) - np.min(dist_mat_copy, axis=1)
            argsort = np.argsort(priority)[::-1] # descending order
        
        return labels 

if __name__ == "__main__":
    from sklearn.datasets import make_blobs
    from matplotlib import pyplot as plt
    from seaborn import scatterplot as scatter
    from sklearn.metrics.pairwise import haversine_distances
    n_samples = 2000
    n_clusters = 4  # use 3 bins for calibration_curve as we have 3 clusters here
    centers = [(-5, -5), (0, 0), (5, 5), (7, 10)]

    X, _ = make_blobs(n_samples=n_samples, n_features=2, cluster_std=1.0,
                    centers=centers, shuffle=False, random_state=42)

    # X = np.random.rand(n_samples, 2)
    equal = SameSizeKMeans(n_clusters)
    equal.fit(X)

    fcm_centers = equal.centers
    fcm_labels = equal.labels

    f, axes = plt.subplots(1, 2, figsize=(11,5))
    scatter(X[:,0], X[:,1], ax=axes[0])
    scatter(X[:,0], X[:,1], ax=axes[1], hue=fcm_labels)
    scatter(fcm_centers[:, 0], fcm_centers[:, 1], ax=axes[1],marker="s",s=200)
    plt.show()