#!usr/bin/python 3.7
#-*-coding:utf-8-*-

'''
@file: fcm.py, fuzzy c-means algorithm
@Author: Jing Wang (jingw2@foxmail.com)
@Date: 06/06/2020
@paper: Clustering with Size Constraints
@github reference: https://github.com/omadson/fuzzy-c-means/blob/master/fcmeans/fcm.py
'''

from scipy.spatial.distance import cdist
import numpy as np 
from scipy.linalg import norm
import base

class FCM(base.Base):
    
    def __init__(self, n_clusters, \
        max_iters=1000, m=2, 
        epsilon=1e-5,
        random_state=42, 
        distance_func=cdist):
        '''
        Args:
            n_clusters (int): number of clusters 
            max_iters (int): maximum iterations
            m (float): membership order, in general it is 2 
            epsilon (float): 1e-5
            random_state (int): random seed
            distance_func (callable function/None), default is Euclidean distance
        '''
        super(FCM, self).__init__(n_clusters, max_iters, distance_func)
        assert m > 1
        self.m = m 
        self.epsilon = epsilon
        self.random_state = random_state
        self.u, self.centers = None, None

    def fit(self, X):
        '''
        Args:
            X (array like): shape is (n_samples, n_dimensions)
        '''
        np.random.seed(self.random_state)
        assert self.n_clusters >= 1 
        n_samples, n_dimensions = X.shape

        # initialize mu 
        self.u = np.random.random(size=(n_samples, self.n_clusters))
        self.u /= np.sum(self.u, axis=1).reshape((-1, 1))

        # initialize centers
        itr = 0
        while True:
            last_u = self.u.copy()
            # update centers
            self.centers = self.update_centers(X) 
            # update membership
            self.u = self.predict(X)
            if norm(self.u - last_u) < self.epsilon or itr >= self.max_iters:
                break 
            itr += 1

    def update_centers(self, X):
        '''
        Update centers based new u
        '''
        um = np.power(self.u, self.m) # (n_samples, n_clusters)
        centers = (X.T.dot(um)).T / np.sum(um, axis=0).reshape((-1, 1))
        return centers

    def predict(self, X):
        power = 2. / (self.m - 1)
        n_samples, n_dimensions = X.shape
        dist = self.distance_func(X, self.centers)
        dist = np.power(dist, power)
        u = dist * np.sum(1. / dist, axis=1).reshape((-1, 1))
        u = 1. / u
        # normalize
        u /= np.sum(u, axis=1).reshape((-1, 1))
        return u

if __name__ == "__main__":
    from sklearn.datasets import make_blobs
    from matplotlib import pyplot as plt
    from seaborn import scatterplot as scatter
    from sklearn.metrics.pairwise import haversine_distances
    n_samples = 5000
    n_bins = 4  # use 3 bins for calibration_curve as we have 3 clusters here
    centers = [(-5, -5), (0, 0), (5, 5), (7, 10)]

    X, _ = make_blobs(n_samples=n_samples, n_features=2, cluster_std=1.0,
                    centers=centers, shuffle=False, random_state=42)

    X = np.radians(X)
    distance_func = haversine_distances
    fcm = FCM(n_bins, distance_func=distance_func)
    fcm.fit(X)

    fcm_centers = fcm.centers
    fcm_labels = fcm.u.argmax(axis=1)


    # plot result
    f, axes = plt.subplots(1, 2, figsize=(11,5))
    scatter(X[:,0], X[:,1], ax=axes[0])
    scatter(X[:,0], X[:,1], ax=axes[1], hue=fcm_labels)
    scatter(fcm_centers[:,0], fcm_centers[:,1], ax=axes[1],marker="s",s=200)
    plt.show()