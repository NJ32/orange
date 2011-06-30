"""
########################################
Reliability estimation (``reliability``)
########################################

.. index:: Reliability Estimation

.. index::
   single: reliability; Reliability Estimation for Regression

*************************************
Reliability Estimation for Regression
*************************************

This module includes different implementations of algorithm used for
predicting reliability of single predictions. Most of the algorithm are taken
from Comparison of approaches for estimating reliability of individual
regression predictions, Zoran Bosnic 2008.

The following example shows a basic usage of reliability estimates
(`reliability-run.py`_, uses `housing.tab`_):

.. literalinclude:: code/reliability-run.py

Reliability estimation methods are computationaly quite hard so it may take
a bit of time for this script to produce a result. In the above example we
first create a learner that we're interested in, in this example
k-nearest-neighbours, and use it inside reliability learner and do cross
validation to get the results. Now we output for the first example in the
dataset all the reliability estimates and their names.

Reliability Methods
===================

Sensitivity Analysis (SAvar and SAbias)
---------------------------------------
.. autoclass:: SensitivityAnalysis

Variance of bagged models (BAGV)
--------------------------------
.. autoclass:: BaggingVariance

Local cross validation reliability estimate (LCV)
-------------------------------------------------
.. autoclass:: LocalCrossValidation

Local modeling of prediction error (CNK)
----------------------------------------
.. autoclass:: CNeighbours

Bagging variance c-neighbours (BVCK)
------------------------------------

.. autoclass:: BaggingVarianceCNeighbours

Mahalanobis distance
--------------------

.. autoclass:: Mahalanobis

Reliability estimate learner
============================

.. autoclass:: Learner

.. autofunction:: get_pearson_r

.. autofunction:: get_pearson_r_by_iterations

Referencing
===========

These methods can be referenced using constants inside the module. For setting,
which methods to use after creating learner, like this::

  reliability.use[Orange.evaluation.reliability.DO_SA] = False
  reliability.use[Orange.evaluation.reliability.DO_BAGV] = True
  reliability.use[Orange.evaluation.reliability.DO_CNK] = False
  reliability.use[Orange.evaluation.reliability.DO_LCV] = True
  reliability.use[Orange.evaluation.reliability.DO_BVCK] = False
  reliability.use[Orange.evaluation.reliability.DO_MAHAL] = False

There is also a dictionary named :data:`METHOD_NAME` which has stored names of
all the reliability estimates::

  METHOD_NAME = {0: "SAvar absolute", 1: "SAbias signed", 2: "SAbias absolute",
                 3: "BAGV absolute", 4: "CNK signed", 5: "CNK absolute",
                 6: "LCV absolute", 7: "BVCK_absolute", 8: "Mahalanobis absolute",
                 10: "ICV"}

and also two constants for saying whether the estimate is signed or it's an
absolute value::

  SIGNED = 0
  ABSOLUTE = 1

Example of usage
================

Here we will walk through a bit longer example of how to use the reliability
estimate module (`reliability-long.py`_, uses `prostate.tab`_):.

.. literalinclude:: code/reliability-long.py
    :lines: 1-16

After loading the Orange library we open out dataset. We chose to work with
the kNNLearner, that also works on regression problems. Create out reliability
estimate learner and test it with cross validation. 
Estimates are then compared using Pearson's coefficient to the prediction error.
The p-values are also computed::

  Estimate               r       p
  SAvar absolute        -0.077   0.454
  SAbias signed         -0.165   0.105
  SAbias absolute       -0.099   0.333
  BAGV absolute          0.104   0.309
  CNK signed             0.233   0.021
  CNK absolute           0.057   0.579
  LCV absolute           0.069   0.504
  BVCK_absolute          0.092   0.368
  Mahalanobis absolute   0.091   0.375

.. literalinclude:: code/reliability-long.py
    :lines: 18-28

Outputs::

  Estimate               r       p
  BAGV absolute          0.126   0.220
  CNK signed             0.233   0.021
  CNK absolute           0.057   0.579
  LCV absolute           0.069   0.504
  BVCK_absolute          0.105   0.305
  Mahalanobis absolute   0.091   0.375


As you can see in the above code you can also chose with reliability estimation
method do you want to use. You might want to do this to reduce computation time 
or because you think they don't perform good enough.

.. literalinclude:: code/reliability-long.py
    :lines: 30-43

In this part of the example we have a usual prediction problem, we have a 
training part of dataset and testing part of dataset. We wrap out learner and
choose to use internal cross validation and no other reliability estimate. 

Internal cross validation is performed on the training part of dataset and it
chooses the best method. Now this method is training on whole training dataset
and used on test dataset to estimate the reliabiliy.

We are interested in the most reliable examples in our testing dataset. We
extract the estimates and id's, sort them and output them.

.. _reliability-run.py: code/reliability-run.py
.. _housing.tab: code/housing.tab

.. _reliability-long.py: code/reliability-long.py
.. _prostate.tab: code/prostate.tab


References
==========

Bosnic Z, Kononenko I (2007) `Estimation of individual prediction reliability using local
sensitivity analysis. <http://www.springerlink.com/content/e27p2584387532g8/>`_
*Applied Intelligence* 29(3), 187-203.

Bosnic Z, Kononenko I (2008) `Comparison of approaches for estimating reliability of 
individual regression predictions.
<http://www.sciencedirect.com/science/article/pii/S0169023X08001080>`_
*Data & Knowledge Engineering* 67(3), 504-516.

Bosnic Z, Kononenko I (2010) `Automatic selection of reliability estimates for individual 
regression predictions.
<http://journals.cambridge.org/abstract_S0269888909990154>`_
*The Knowledge Engineering Review* 25(1), 27-47.

"""
import Orange

import random
import statc
import math
import warnings

# Labels and final variables
labels = ["SAvar", "SAbias", "BAGV", "CNK", "LCV", "BVCK", "Mahalanobis", "ICV"]

# All the estimators calculation constants
DO_SA = 0
DO_BAGV = 1
DO_CNK = 2
DO_LCV = 3
DO_BVCK = 4
DO_MAHAL = 5

# All the estimator method constants
SAVAR_ABSOLUTE = 0
SABIAS_SIGNED = 1
SABIAS_ABSOLUTE = 2
BAGV_ABSOLUTE = 3
CNK_SIGNED = 4
CNK_ABSOLUTE = 5
LCV_ABSOLUTE = 6
BVCK_ABSOLUTE = 7
MAHAL_ABSOLUTE = 8
ICV_METHOD = 10

# Type of estimator constant
SIGNED = 0
ABSOLUTE = 1

# Names of all the estimator methods
METHOD_NAME = {0: "SAvar absolute", 1: "SAbias signed", 2: "SAbias absolute",
               3: "BAGV absolute", 4: "CNK signed", 5: "CNK absolute",
               6: "LCV absolute", 7: "BVCK_absolute", 8: "Mahalanobis absolute",
               10: "ICV"}

def get_reliability_estimation_list(res, i):
    return [result.probabilities[0].reliability_estimate[i].estimate for result in res.results], res.results[0].probabilities[0].reliability_estimate[i].signed_or_absolute, res.results[0].probabilities[0].reliability_estimate[i].method

def get_prediction_error_list(res):
    return [result.actualClass - result.classes[0] for result in res.results]

def get_pearson_r(res):
    """
    Returns Pearsons coefficient between the prediction error and each of the
    used reliability estimates. Function also return the p-value of each of
    the coefficients.
    """
    prediction_error = get_prediction_error_list(res)
    results = []
    for i in xrange(len(res.results[0].probabilities[0].reliability_estimate)):
        reliability_estimate, signed_or_absolute, method = get_reliability_estimation_list(res, i)
        try:
            if signed_or_absolute == SIGNED:
                r, p = statc.pearsonr(prediction_error, reliability_estimate)
            else:
                r, p = statc.pearsonr([abs(pe) for pe in prediction_error], reliability_estimate)
        except Exception:
            r = p = float("NaN")
        results.append((r, p, signed_or_absolute, method))
    return results

def get_pearson_r_by_iterations(res):
    """
    Returns average Pearsons coefficient over all folds between prediction error
    and each of the used estimates.
    """
    results_by_fold = Orange.evaluation.scoring.split_by_iterations(res)
    number_of_estimates = len(res.results[0].probabilities[0].reliability_estimate)
    number_of_examples = len(res.results)
    number_of_folds = len(results_by_fold)
    results = [0 for _ in xrange(number_of_estimates)]
    sig = [0 for _ in xrange(number_of_estimates)]
    method_list = [0 for _ in xrange(number_of_estimates)]
    
    for res in results_by_fold:
        prediction_error = get_prediction_error_list(res)
        for i in xrange(number_of_estimates):
            reliability_estimate, signed_or_absolute, method = get_reliability_estimation_list(res, i)
            try:
                if signed_or_absolute == SIGNED:
                    r, _ = statc.pearsonr(prediction_error, reliability_estimate)
                else:
                    r, _ = statc.pearsonr([abs(pe) for pe in prediction_error], reliability_estimate)
            except Exception:
                r = float("NaN")
            results[i] += r
            sig[i] = signed_or_absolute
            method_list[i] = method
    
    # Calculate p-values
    results = [float(res) / number_of_folds for res in results]
    ps = [p_value_from_r(r, number_of_examples) for r in results]
    
    return zip(results, ps, sig, method_list)

def p_value_from_r(r, n):
    """
    Calculate p-value from the paerson coefficient and the sample size.
    """
    df = n - 2
    t = r * (df /((-r + 1.0 + 1e-30) * (r + 1.0 + 1e-30)) )**0.5
    return statc.betai (df * 0.5, 0.5, df/(df + t*t))

class Estimate:
    def __init__(self, estimate, signed_or_absolute, method, icv_method = -1):
        self.estimate = estimate
        self.signed_or_absolute = signed_or_absolute
        self.method = method
        self.method_name = METHOD_NAME[method]
        self.icv_method = icv_method
        self.icv_method_name = METHOD_NAME[icv_method] if icv_method != -1 else ""
        
class SensitivityAnalysis:
    """
    
    :param e: List of possible e values for SAvar and SAbias reliability estimates, the default value is [0.01, 0.1, 0.5, 1.0, 2.0].
    :type e: list of floats
    
    :rtype: :class:`Orange.evaluation.reliability.SensitivityAnalysisClassifier`
    
    To estimate the reliabilty for given example we extend the learning set 
    with given example and labeling it with :math:`K + \epsilon (l_{max} - l_{min})`,
    where K denotes the initial prediction, :math:`\epsilon` is sensitivity parameter and
    :math:`l_{min}` and :math:`l_{max}` denote lower and the upper bound of
    the learning examples. After computing different sensitivity predictions
    using different values of e, the prediction are combined into SAvar and SAbias.
    SAbias can be used as signed estimate or as absolute value of SAbias. 

    :math:`SAvar = \\frac{\sum_{\epsilon \in E}(K_{\epsilon} - K_{-\epsilon})}{|E|}`

    :math:`SAbias = \\frac{\sum_{\epsilon \in E} (K_{\epsilon} - K ) + (K_{-\epsilon} - K)}{2 |E|}`
    
    
    """
    def __init__(self, e=[0.01, 0.1, 0.5, 1.0, 2.0]):
        self.e = e
    
    def __call__(self, examples, learner):
        min_value = max_value = examples[0].getclass().value
        for ex in examples:
            if ex.getclass().value > max_value:
                max_value = ex.getclass().value
            if ex.getclass().value < min_value:
                min_value = ex.getclass().value
        return SensitivityAnalysisClassifier(self.e, examples, min_value, max_value, learner)
    
class SensitivityAnalysisClassifier:
    def __init__(self, e, examples, max_value, min_value, learner):
        self.e = e
        self.examples = examples
        self.max_value = max_value
        self.min_value = min_value
        self.learner = learner
    
    def __call__(self, example, predicted, probabilities):
        # Create new dataset
        r_data = Orange.data.Table(self.examples)
        
        # Create new example
        modified_example = Orange.data.Instance(example)
        
        # Append it to the data
        r_data.append(modified_example)
        
        # Calculate SAvar & SAbias
        SAvar = SAbias = 0
        
        for eps in self.e:
            # +epsilon
            r_data[-1].setclass(predicted.value + eps*(self.max_value - self.min_value))
            c = self.learner(r_data)
            k_plus = c(example, Orange.core.GetValue)
            
            # -epsilon
            r_data[-1].setclass(predicted.value - eps*(self.max_value - self.min_value))
            c = self.learner(r_data)
            k_minus = c(example, Orange.core.GetValue)
            #print len(r_data)
            #print eps*(self.max_value - self.min_value)
            #print k_plus
            #print k_minus
            # calculate part SAvar and SAbias
            SAvar += k_plus.value - k_minus.value
            SAbias += k_plus.value + k_minus.value - 2*predicted.value
        
        SAvar /= len(self.e)
        SAbias /= 2*len(self.e)
        
        return [Estimate(SAvar, ABSOLUTE, SAVAR_ABSOLUTE),
                Estimate(SAbias, SIGNED, SABIAS_SIGNED),
                Estimate(abs(SAbias), ABSOLUTE, SABIAS_ABSOLUTE)]
    
class BaggingVariance:
    """
    
    :param m: Number of bagged models to be used with BAGV estimate
    :type m: int
    
    :rtype: :class:`Orange.evaluation.reliability.BaggingVarianceClassifier`
    
    We construct m different bagging models of the original chosen learner and use
    those predictions (:math:`K_i, i = 1, ..., m`) of given example to calculate the variance, which we use as
    reliability estimator.

    :math:`BAGV = \\frac{1}{m} \sum_{i=1}^{m} (K_i - K)^2`

    where

    :math:`K = \\frac{\sum_{i=1}^{m} K_i}{m}`
    
    """
    def __init__(self, m=50):
        self.m = m
    
    def __call__(self, examples, learner):
        classifiers = []
        
        # Create bagged classifiers using sampling with replacement
        for _ in xrange(self.m):
            selection = [random.randrange(len(examples)) for _ in xrange(len(examples))]
            data = examples.getitems(selection)
            classifiers.append(learner(data))
        return BaggingVarianceClassifier(classifiers)

class BaggingVarianceClassifier:
    def __init__(self, classifiers):
        self.classifiers = classifiers
    
    def __call__(self, example, *args):
        BAGV = 0
        
        # Calculate the bagging variance
        bagged_values = [c(example, Orange.core.GetValue).value for c in self.classifiers]
        
        k = sum(bagged_values) / len(bagged_values)
        
        BAGV = sum( (bagged_value - k)**2 for bagged_value in bagged_values) / len(bagged_values)
        
        return [Estimate(BAGV, ABSOLUTE, BAGV_ABSOLUTE)]
        
class LocalCrossValidation:
    """
    
    :param k: Number of nearest neighbours used in LCV estimate
    :type k: int
    
    :rtype: :class:`Orange.evaluation.reliability.LocalCrossValidationClassifier`
    
    We find k nearest neighbours to the given example and put them in
    seperate dataset. On this dataset we do leave one out
    validation using given model. Reliability estimate is then distance
    weighted absolute prediction error.
    
    1. define the set of k nearest neighours :math:`N = { (x_1, x_1),..., (x_k, c_k)}`
    2. FOR EACH :math:`(x_i, c_i) \in N`
    
      2.1. generare model M on :math:`N \\backslash (x_i, c_i)`
    
      2.2. for :math:`(x_i, c_i)` compute LOO prediction :math:`K_i`
    
      2.3. for :math:`(x_i, c_i)` compute LOO error :math:`E_i = | C_i - K_i |`
    
    3. :math:`LCV(x) = \\frac{ \sum_{(x_i, c_i) \in N} d(x_i, x) * E_i }{ \sum_{(x_i, c_i) \in N} d(x_i, x) }`
    
    """
    def __init__(self, k=5):
        self.k = k
    
    def __call__(self, examples, learner):
        nearest_neighbours_constructor = Orange.classification.knn.FindNearestConstructor()
        nearest_neighbours_constructor.distanceConstructor = Orange.distances.EuclideanConstructor()
        
        distance_id = Orange.core.newmetaid()
        nearest_neighbours = nearest_neighbours_constructor(examples, 0, distance_id)
        
        return LocalCrossValidationClassifier(distance_id, nearest_neighbours, self.k, learner)

class LocalCrossValidationClassifier:
    def __init__(self, distance_id, nearest_neighbours, k, learner):
        self.distance_id = distance_id
        self.nearest_neighbours = nearest_neighbours
        self.k = k
        self.learner = learner
    
    def __call__(self, example, *args):
        LCVer = 0
        LCVdi = 0
        
        # Find k nearest neighbors
        
        knn = [ex for ex in self.nearest_neighbours(example, self.k)]
        
        # leave one out of prediction error
        for i in xrange(len(knn)):
            train = knn[:]
            del train[i]
            
            classifier = self.learner(Orange.data.Table(train))
            
            returned_value = classifier(knn[i], Orange.core.GetValue)
            
            e = abs(knn[i].getclass().value - returned_value.value)
            
            LCVer += e * math.exp(-knn[i][self.distance_id])
            LCVdi += math.exp(-knn[i][self.distance_id])
        
        LCV = LCVer / LCVdi if LCVdi != 0 else 0
        
        return [ Estimate(LCV, ABSOLUTE, LCV_ABSOLUTE) ]

class CNeighbours:
    """
    
    :param k: Number of nearest neighbours used in CNK estimate
    :type k: int
    
    :rtype: :class:`Orange.evaluation.reliability.CNeighboursClassifier`
    
    Estimate CNK is defined for unlabeled example as difference between
    average label of the nearest neighbours and the examples prediction. CNK can
    be used as a signed estimate or only as absolute value. 
    
    :math:`CNK = \\frac{\sum_{i=1}^{k}C_i}{k} - K`
    
    Where k denotes number of neighbors, C :sub:`i` denotes neighbours' labels and
    K denotes the example's prediction.
    
    """
    def __init__(self, k=5):
        self.k = k
    
    def __call__(self, examples, learner):
        nearest_neighbours_constructor = Orange.classification.knn.FindNearestConstructor()
        nearest_neighbours_constructor.distanceConstructor = Orange.distances.EuclideanConstructor()
        
        distance_id = Orange.core.newmetaid()
        nearest_neighbours = nearest_neighbours_constructor(examples, 0, distance_id)
        return CNeighboursClassifier(nearest_neighbours, self.k)

class CNeighboursClassifier:
    def __init__(self, nearest_neighbours, k):
        self.nearest_neighbours = nearest_neighbours
        self.k = k
    
    def __call__(self, example, predicted, probabilities):
        CNK = 0
        
        # Find k nearest neighbors
        
        knn = [ex for ex in self.nearest_neighbours(example, self.k)]
        
        # average label of neighbors
        for ex in knn:
            CNK += ex.getclass().value
        
        CNK /= self.k
        CNK -= predicted.value
        
        return [Estimate(CNK, SIGNED, CNK_SIGNED),
                Estimate(abs(CNK), ABSOLUTE, CNK_ABSOLUTE)]
    
class Mahalanobis:
    """
    
    :param k: Number of nearest neighbours used in Mahalanobis estimate
    :type k: int
    
    :rtype: :class:`Orange.evaluation.reliability.MahalanobisClassifier`
    
    Mahalanobis distance estimate is defined as `mahalanobis distance <http://en.wikipedia.org/wiki/Mahalanobis_distance>`_ to the
    k nearest neighbours of chosen example.

    
    """
    def __init__(self, k=3):
        self.k = k
    
    def __call__(self, examples, *args):
        nnm = Orange.classification.knn.FindNearestConstructor()
        nnm.distanceConstructor = Orange.distances.MahalanobisConstructor()
        
        mid = Orange.core.newmetaid()
        nnm = nnm(examples, 0, mid)
        return MahalanobisClassifier(self.k, nnm, mid)

class MahalanobisClassifier:
    def __init__(self, k, nnm, mid):
        self.k = k
        self.nnm = nnm
        self.mid = mid
    
    def __call__(self, example, *args):
        mahalanobis_distance = 0
        
        mahalanobis_distance = sum(ex[self.mid].value for ex in self.nnm(example, self.k))
        
        return [ Estimate(mahalanobis_distance, ABSOLUTE, MAHAL_ABSOLUTE) ]

class BaggingVarianceCNeighbours:
    """
    
    :param bagv: Instance of Bagging Variance estimator.
    :type bagv: :class:`Orange.evaluation.reliability.BaggingVariance`
    
    :param cnk: Instance of CNK estimator.
    :type cnk: :class:`Orange.evaluation.reliability.CNeighbours`
    
    :rtype: :class:`Orange.evaluation.reliability.BaggingVarianceCNeighboursClassifier`
    
    BVCK is a combination of Bagging variance and local modeling of prediction
    error, for this estimate we take the average of both.
    
    """
    def __init__(self, bagv=BaggingVariance(), cnk=CNeighbours()):
        self.bagv = bagv
        self.cnk = cnk
    
    def __call__(self, examples, learner):
        bagv_classifier = self.bagv(examples, learner)
        cnk_classifier = self.cnk(examples, learner)
        return BaggingVarianceCNeighboursClassifier(bagv_classifier, cnk_classifier)

class BaggingVarianceCNeighboursClassifier:
    def __init__(self, bagv_classifier, cnk_classifier):
        self.bagv_classifier = bagv_classifier
        self.cnk_classifier = cnk_classifier
    
    def __call__(self, example, predicted, probabilities):
        bagv_estimates = self.bagv_classifier(example, predicted, probabilities)
        cnk_estimates = self.cnk_classifier(example, predicted, probabilities)
        
        bvck_value = (bagv_estimates[0].estimate + cnk_estimates[1].estimate)/2
        bvck_estimates = [ Estimate(bvck_value, ABSOLUTE, BVCK_ABSOLUTE) ]
        bvck_estimates.extend(bagv_estimates)
        bvck_estimates.extend(cnk_estimates)
        return bvck_estimates

class Learner:
    """
    Reliability estimation wrapper around a learner we want to test.
    Different reliability estimation algorithms can be used on the
    chosen learner. This learner works as any other and can be used as one.
    The only difference is when the classifier is called with a given
    example instead of only return the value and probabilities, it also
    attaches a list of reliability estimates to 
    :data:`probabilities.reliability_estimate`.
    Each reliability estimate consists of a tuple 
    (estimate, signed_or_absolute, method).
    
    :param e: List of possible e value for SAvar and SAbias reliability estimate
    :type e: list of floats
    
    :param m: Number of bagged models to be used with BAGV estimate
    :type m: int
    
    :param cnk_k: Number of nearest neighbours used in CNK estimate
    :type cnk_k: int
    
    :param lcv_k: Number of nearest neighbours used in LCV estimate
    :type cnk_k: int
    
    :param icv: Use internal cross-validation. Internal cross-validation calculates all
                the reliability estimates on the training data using cross-validation.
                Then it chooses the most successful estimate and uses it on the test
                dataset.
    :type icv: boolean
    
    :param use: List of booleans saying which reliability methods should be
                used in our experiment and which not.
    :type use: list of booleans
    
    :param use_with_icv: List of booleans saying which reliability methods
                         should be used in inside cross validation and
                         which not.
    
    :type use_with_icv: list of booleans
    
    :rtype: :class:`Orange.evaluation.reliability.Learner`
    """
    def __init__(self, box_learner, name="Reliability estimation",
                 estimators = [SensitivityAnalysis(),
                               BaggingVariance(),
                               LocalCrossValidation(),
                               CNeighbours(),
                               Mahalanobis()], **kwds):
        self.__dict__.update(kwds)
        self.name = name
        self.estimators = estimators
        self.box_learner = box_learner
        
    
    def __call__(self, examples, weight=None, **kwds):
        """Learn from the given table of data instances.
        
        :param instances: Data instances to learn from.
        :type instances: Orange.data.Table
        :param weight: Id of meta attribute with weights of instances
        :type weight: integer
        :rtype: :class:`Orange.evaluation.reliability.Classifier`
        """
        return Classifier(examples, self.box_learner, self.estimators)
    
    def internal_cross_validation(self, examples, folds=10):
        """ Performs internal cross validation (as in Automatic selection of
        reliability estimates for individual regression predictions,
        Zoran Bosnic 2010) and return id of the method
        that scored best on this data. """
        cv_indices = Orange.core.MakeRandomIndicesCV(examples, folds)
        
        list_of_rs = []
        
        sum_of_rs = defaultdict(float)
        
        for fold in xrange(folds):
            data = examples.select(cv_indices, fold)
            res = Orange.evaluation.testing.crossValidation([self], data)
            results = get_pearson_r(res)
            for r, _, _, method in results:
                sum_of_rs[method] += r
        sorted_sum_of_rs = sorted(sum_of_rs.items(), key=lambda estimate: estimate[1], reverse=True)
        return sorted_sum_of_rs[0][0]
    
    labels = ["SAvar", "SAbias", "BAGV", "CNK", "LCV", "BVCK", "Mahalanobis", "ICV"]

class Classifier:
    def __init__(self, examples, box_learner, estimators, **kwds):
        self.__dict__.update(kwds)
        self.examples = examples
        self.box_learner = box_learner
        self.estimators = estimators
        
        # Train the learner with original data
        self.classifier = box_learner(examples)
        
        # Train all the estimators and create their classifiers
        self.estimation_classifiers = [estimator(examples, box_learner) for estimator in estimators]
    
    def __call__(self, example, result_type=Orange.core.GetValue):
        """
        Classifiy and estimate a new instance. When you chose 
        Orange.core.GetBoth or Orange.core.getProbabilities, you can access 
        the reliability estimates inside probabilities.reliability_estimate.
        
        :param instance: instance to be classified.
        :type instance: :class:`Orange.data.Instance`
        :param result_type: :class:`Orange.classification.Classifier.GetValue` or \
              :class:`Orange.classification.Classifier.GetProbabilities` or
              :class:`Orange.classification.Classifier.GetBoth`
        
        :rtype: :class:`Orange.data.Value`, 
              :class:`Orange.statistics.Distribution` or a tuple with both
        """
        predicted, probabilities = self.classifier(example, Orange.core.GetBoth)
        
        # Create a place holder for estimates
        if probabilities is None:
            probabilities = Orange.statistics.distribution.Continuous()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            probabilities.reliability_estimate = []
        
        # Calculate all the estimates and add them to the results
        for estimate in self.estimation_classifiers:
            probabilities.reliability_estimate.extend(estimate(example, predicted, probabilities))
        
        # Return the appropriate type of result
        if result_type == Orange.core.GetValue:
            return predicted
        elif result_type == Orange.core.GetProbabilities:
            return probabilities
        else:
            return predicted, probabilities