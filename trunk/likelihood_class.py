#!/usr/bin/env python
#
# Name:  likelihood_class
#
# Author: Thuso S Simon
#
# Date: 25 of April, 2013
#TODO: 
#
#    vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
#    Copyright (C) 2013 Thuso S Simon
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    For the GNU General Public License, see <http://www.gnu.org/licenses/>.
#    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#History (version,date, change author)
#
#
#
""" Likelihood classes for running of MCMC, RJMCMC and other fitting methods. 
First class is and example and has all required methods needed to run MCMC or
RJMCMC. Also has specific classes for use of spectral fitting"""

import numpy as nu
from glob import glob
import Age_date as ag
import ezgal as gal
import scipy.stats as stats_dist
import multiprocessing as multi
from itertools import izip

class Example_lik_class(object):

    '''exmaple class for use with RJCMCM or MCMC program, all methods are
    required and inputs are required till the comma, and outputs are also
    not mutable. The body of the class can be filled in to users delight'''

    def __init__(self,):
        '''(Example_lik_class,#user defined) -> NoneType or userdefined

        initalize class, can do whatever you want. User to define functions'''
        #return #whatever you want or optional
        pass


    def proposal(self,mu,sigma):
        '''(Example_lik_class, ndarray,ndarray) -> ndarray
        Proposal distribution, draws steps for chain. Should use a symetric
        distribution'''
        
        #return up_dated_param 
        pass

    def lik(self,param):
        '''(Example_lik_class, ndarray) -> float
        Calculates likelihood for input parameters. Outuputs log-likelyhood'''
        
        #return loglik
        pass

    def prior(self,param):
        '''(Example_lik_class, ndarray) -> float
        Calculates log-probablity for prior'''
        #return logprior
        pass


    def model_prior(self,model):
        '''(Example_lik_class, any type) -> float
        Calculates log-probablity prior for models. Not used in MCMC and
        is optional in RJMCMC.'''
        #return log_model
        pass

    def initalize_param(self,model):
        '''(Example_lik_class, any type) -> ndarray, ndarray

        Used to initalize all starting points for run of RJMCMC and MCMC.
        outputs starting point and starting step size'''
        #return init_param, init_step
        pass

        
    def step_func(self,step_crit,param,step_size,model):
        '''(Example_lik_class, float, ndarray or list, ndarray, any type) ->
        ndarray

        Evaluates step_criteria, with help of param and model and 
        changes step size during burn-in perior. Outputs new step size
        '''
        #return new_step
        pass

    def birth_death(self,birth_rate, model, param):
        '''(Example_lik_class, float, any type, dict(ndarray)) -> 
           dict(ndarray), any type, bool, float

        For RJMCMC only. Does between model move. Birth rate is probablity to
        move from one model to another, models is current model and param is 
        dict of all localtions in param space. 
        Returns new param array with move updated, key for new model moving to,
        whether of not to attempt model jump (False to make run as MCMC) and the
        Jocobian for move.
        '''
        #for RJCMC
        #return new_param, try_model, attemp_jump, Jocobian
        #for MCMC
        #return None, None, False, None
        pass

#=============================================
#spectral fitting with RJCMC Class
class VESPA_fit(object):
    '''Finds the age, metalicity, star formation history, 
    dust obsorption and line of sight velocity distribution
    to fit a Spectrum.

    Uses vespa methodology splitting const sfh into multiple componets
    '''
    def __init__(self,data, min_sfh=1,max_sfh=16,lin_space=False,use_dust=True, 
		use_losvd=True, spec_lib='p2',imf='salp',
			spec_lib_path='/home/thuso/Phd/stellar_models/ezgal/'):
		'''(VESPA_fitclass, ndarray,int,int) -> NoneType
        data - spectrum to fit
        *_sfh - range number of burst to allow
        lin_space - make age bins linearly space or log spaced
        use_* allow useage of dust and line of sigt velocity dispersion
        spec_lib - spectral lib to use
        imf - inital mass function to use
        spec_lib_path - path to ssps
        sets up vespa like fits
		'''
		self.data = nu.copy(data)
		#make mean value of data= 1000
		self._norm = 1./(self.data[:,1].mean()/1000.)
		self.data[:,1] *= self._norm
        #load models
		cur_lib = ['basti', 'bc03', 'cb07','m05','c09','p2']
		assert spec_lib.lower() in cur_lib, ('%s is not in ' %spec_lib.lower() + str(cur_lib))
		if not spec_lib_path.endswith('/') :
			spec_lib_path += '/'
		models = glob(spec_lib_path+spec_lib+'*'+imf+'*')
		if len(models) == 0:
			models = glob(spec_lib_path+spec_lib.lower()+'*'+imf+'*')
		assert len(models) > 0, "Did not find any models"
        #crate ezgal class of models
		SSP = gal.wrapper(models)
        #extract seds from ezgal wrapper
		spect, info = [SSP.sed_ls], []
		for i in SSP:
			metal = float(i.meta_data['met'])
			ages = nu.float64(i.ages)
			for j in ages:
				if j == 0:
					continue
				spect.append(i.get_sed(j,age_units='yrs'))
				info.append([metal+0,j])
		info,self._spect = [nu.log10(info),None],nu.asarray(spect).T
		#set hidden varibles
		self._lib_vals = info
		self._age_unq = nu.unique(info[0][:,1])
		self._metal_unq = nu.unique(info[0][:,0])
		self._lib_vals[0][:,0] = 10**self._lib_vals[0][:,0]
		self._min_sfh, self._max_sfh = min_sfh,max_sfh
		#params
		self.curent_param = nu.empty(2)
		self.models = {}
		for i in xrange(min_sfh,max_sfh+1):
			self.models[str(i)]= ['burst_length','mean_age', 'metal','norm'] * i
		'''
		self.data = nu.copy(data)
        #normalized so area under curve is 1 to keep chi 
        #values resonalble
        #need to properly handel uncertanty
        self.norms = self.area_under_curve(data) * 10 ** -5 #need to turn off
        self.data[:,1] = self.data[:, 1] / self.norms

        #initalize bound varables
        lib_vals = get_fitting_info(lib_path)
        #to keep roundoff error constistant
        lib_vals[0][:,0] = nu.log10(lib_vals[0][:, 0]) 
        metal_unq = nu.unique(lib_vals[0][:, 0])
        #get boundary of parameters
        self.hull = bound.find_boundary(lib_vals[0])
        lib_vals[0][:,0] = 10**lib_vals[0][:,0]
        age_unq = nu.unique(lib_vals[0][:, 1])
        self._lib_vals = lib_vals
        self._age_unq = age_unq
        self._metal_unq = metal_unq
        self._option = option
        self._cpus = cpus
        self.bins = bins
        self._burnin = burnin
        self._iter = itter
        #set prior info for age, and metalicity
        self.metal_bound = nu.array([metal_unq.min(),metal_unq.max()])
        #dust options
        self._dust = use_dust
        self.dust_bound = nu.array([0., 4.])
        #line of sight velocity despersion stuff
        self._losvd = use_lovsd
        self._velocityscale = (nu.diff(self.data[:,0]).mean()
                               / self.data[:,0].mean() * 299792.458)
        #check to see if properties are the same
        self._metal_unq = nu.log10(nu.unique(nu.float64(self.SSP['met'])))
        #self._len_unq = nu.unique(nu.asarray(self.SSP.meta_data['length'],
		#				dtype=float))
			'''	
		
    def proposal(self,mu,sigma):
		'''(Example_lik_class, ndarray,ndarray) -> ndarray
		Proposal distribution, draws steps for chain. Should use a symetric
		distribution'''
		#save length and mean age they don't change
                t_out = nu.random.multivariate_normal(nu.ravel(mu),sigma[0])
		bins = sigma[0].shape[0]/4
		t_out = nu.reshape(t_out, (bins, 4))
		#set length and age back to original and make norm positive
		for i,j in enumerate(mu):
			t_out[i][:2] = j[:2]
			t_out[i][-1] = abs(t_out[i][-1])

		return t_out
        

    def lik(self,param, bins,return_all=False):
        '''(Example_lik_class, ndarray) -> float
        Calculates likelihood for input parameters. Outuputs log-likelyhood'''
        burst_model = {}
        for i in param[bins]:
            burst_model[str(i[1])] = i[3]*ag.make_burst(i[0],i[1],i[2],
                            self._metal_unq, self._age_unq, self._spect, self._lib_vals)
		#do dust

		#do losvd

		#get loglik
            model = nu.sum(burst_model.values(),0)
		#return loglik
            if self.data.shape[1] == 3:
                #uncertanty calc
                pass
            else:
                prob = stats_dist.norm.logpdf(model,self.data[:,1]).sum()
			#prob = -nu.sum((model -	self.data[:,1])**2)
                #return
            if 	return_all:
                return prob, model
            else:
                return prob

    def prior(self,param,bins):
        '''(Example_lik_class, ndarray) -> float
        Calculates log-probablity for prior'''
        #return logprior
        return 0.


    def model_prior(self,model):
        '''(Example_lik_class, any type) -> float
        Calculates log-probablity prior for models. Not used in MCMC and
        is optional in RJMCMC.'''
        #return log_model
        return 0.

    def initalize_param(self,model):
		'''(Example_lik_class, any type) -> ndarray, ndarray

		Used to initalize all starting points for run of RJMCMC and MCMC.
		outputs starting point and starting step size
		'''

		if not int(model) == 1:
			return nu.empty(int(model)*4), nu.identity(4*int(model))
		#make single burst for entire age length
		self.cur_spec = [ ag.make_burst(self._age_unq.ptp(), nu.mean(self._age_unq), self._metal_unq.mean()
										, self._metal_unq, self._age_unq, self._spect, self._lib_vals	)]
		#make step size
		sigma = nu.identity(4)
		#norm 10% of self._norm
		sigma[-1,-1] = .1 * self._norm
		return nu.array([ self._age_unq.ptp(), nu.mean(self._age_unq), self._metal_unq.mean(), self._norm]), sigma

        
    def step_func(self,step_crit,param,step_size,model):
        '''(Example_lik_class, float, ndarray or list, ndarray, any type) ->
        ndarray

        Evaluates step_criteria, with help of param and model and 
        changes step size during burn-in perior. Outputs new step size
        '''
        if step_crit > .60:
            step_size[model][0] *= 1.05
        elif step_crit < .2:
            step_size[model][0] /= 1.05
        #cov matrix
        if len(param) % 2000 == 0 and len(param) > 0.:
            new_shape = nu.prod(param[0].shape)
            step_size[model] = [nu.cov(nu.asarray(param[-2000:]).reshape(2000,new_shape).T)]

        return step_size[model]


    def birth_death(self,birth_rate, model, param):
        '''(Example_lik_class, float, any type, dict(ndarray)) -> 
        dict(ndarray), any type, bool, float
        
        For RJMCMC only. Does between model move. Birth rate is probablity to
        move from one model to another, models is current model and param is 
        dict of all localtions in param space. 
        Returns new param array with move updated, key for new model moving to,
        whether of not to attempt model jump (False to make run as MCMC) and the
        Jocobian for move.
        '''
        if birth_rate > nu.random.rand() and self._max_sfh != int(model):
            #birth!
            temp_model = str(int(model) + 1)
            #split component with higest weight
            temp_param = nu.reshape(param[model], (int(model), 4))
            index = nu.argmax(temp_param[:,-1])
            u = nu.random.rand()
            new_param = ([[temp_param[index,0]/2., 
                           (2*temp_param[index,1] - temp_param[index,0]/2.)/2.,
                           temp_param[index,2] + 0., temp_param[index,3] * u]])

            new_param.append([temp_param[index,0]/2.,
                              (2*temp_param[index,1] + temp_param[index,0]/2.)/2.,
                              temp_param[index,2] + 0., temp_param[index,3] * (1 -u)])
            #copy the rest
            for i in range(int(model)):
                if i == index:
                    continue
                new_param.append(temp_param[i].copy())
            param[temp_model] = nu.asarray(new_param)

        elif self._min_sfh != int(model):
                #death!
                temp_model = str(int(model) - 1)
                #get lowest weight and give random amount to neighbor
                index = param[model][:,-1].argmin()
                new_param = []
                split = param[model][index]
                u = nu.random.rand()
                if index - 1 > -1 :
                    #combine with younger                    
                    temp = param[model][index-1]
                    new_param.append([temp[0] + split[0] * u, 0., temp[2] + split[2] * u,
                                      temp[3] + split[3] * u])
                    new_param[-1][1] = new_param[-1][0]/2. + temp[1] -temp[0]/2.
                if index + 1 < int(model):
                    #combine with older
                    temp = param[model][index+1]
                    new_param.append([temp[0] + split[0] * u, 0., temp[2] + split[2] * u,
                                      temp[3] + split[3] * u])
                    new_param[-1][1] =  new_param[-1][0]/2. + temp[1]-temp[0]/2.
                for i in range(param[model].shape[0]):
                    if i in range(1-index,index+2):
                        continue
                    new_param.append(nu.copy(param[model][i]))
                #set for output
                param[temp_model] = nu.asarray(new_param)

                import cPickle as pik
                pik.dump((birth_rate, model, param),open('birth.pik' ,'w'),2)
                #combine smallest weight with other
                return param, None, False, None
        else:
            #birth or death failed
            return param, None, False, None
        return param, temp_model, True, 1. #need to sort out jacobian

    def make_sfh_plot(self,param, model=None):
        '''(dict(ndarray)-> Nonetype
        Make plot of sfh vs log age of all models in param 
        '''
        import pylab as lab
        if not model is None:
            x,y = [], []
            for i in param[model]:
                x.append(i[1]-i[0]/2.)
                x.append(i[1]+i[0]/2.)
                y.append(i[3])
                y.append(i[3])
            lab.plot(x,y,label=model)
            lab.legend()
            lab.show()
        else:
            for i in param.keys():
                pass

class Spectral_fit(object):
    '''Finds the age, metalicity, star formation history, 
    dust obsorption and line of sight velocity distribution
    to fit a Spectrum. 
    '''

    def __init__(self,data, use_dust=True, use_losvd=True, spec_lib='p2',imf='salp',spec_lib_path='/home/thuso/Phd/stellar_models/ezgal/'):
        '''(Example_lik_class,#user defined) -> NoneType or userdefined

        initalize class, initalize spectal func, put nx2 or nx3 specta
        ndarray (wave,flux,uncert (optional)).

        use_ tells if you want to fit for dust and/or line of sight
        velocity dispersion.
        
        spec_lib is the spectral lib to use. models avalible for use:
        BaSTI - Percival et al. 2009 (ApJ, 690, 472)
        BC03 - Bruzual and Charlot 2003 (MNRAS, 344, 1000)
        CB07 - Currently unpublished. Please reference as an updated BC03 model.
        M05 - Maraston et al. 2005 (MNRAS, 362, 799)
        C09 - Conroy, Gunn, and White 2009 (ApJ, 699, 486C) and Conroy and Gunn 2010 (ApJ, 712, 833C (Please cite both)
        PEGASE2 (p2) - Fioc and Rocca-Volmerange 1997 (A&A, 326, 950)
        More to come!'''
        
        #initalize data and make ezgal class for uses
        self.data = nu.copy(data)
        #check data, reduice wavelenght range, match wavelengths to lib
        #get all ssp libs with spec_lib name
        cur_lib = ['basti', 'bc03', 'cb07','m05','c09','p2']
        assert spec_lib.lower() in cur_lib, ('%s is not in ' %spec_lib.lower() + str(cur_lib))
        if not spec_lib_path.endswith('/') :
            spec_lib_path += '/'
        models = glob(spec_lib_path+spec_lib+'*'+imf+'*')
        if len(models) == 0:
            models = glob(spec_lib_path+spec_lib.lower()+'*'+imf+'*')
        assert len(models) > 0, "Did not find any models"
        #crate ezgal class of models
        self.SSP = gal.wrapper(models)
        #check to see if properties are the same
        self._metal_unq = nu.float64(self.SSP['met'])
        self._age_unq = nu.copy(self.SSP.sed_ages)/10.**9
        #make keys for models (all caps=required, lower not required
        #+ means additive modesl, * is multiplicative or convolution
        self.get_sed = lambda x: x[2] * self.SSP.get_sed(x[0],x[1])
        self.models = {'SSP+':[['age','metal','norm'],self.get_sed],
			'dust*':[['tbc','tsm'],ag.dust]}
        #set values for priors
        
    def _model_handeler(self,models):
        '''(Example_lik_class, str) -> str
        
        Not called by RJMMCMC or MCMC, but handels how models interact
        '''
        pass
		
    def proposal(self,mu,sigma):
        '''(Example_lik_class, ndarray,ndarray) -> ndarray
        Proposal distribution, draws steps for chain. Should use a symetric
        distribution'''
        out = []
        for i in xrange(len(mu)):
            out.append(nu.random.multivariate_normal(mu[i],sigma[i]))

        return out

    def lik(self,param,model):
        '''(Example_lik_class, ndarray, str) -> float
        Calculates likelihood for input parameters. Outuputs log-likelyhood'''
        #get model
        imodel = []
		#get additive models
        for i,j in enumerate(model.split(',')):
            if j.endswith('+'):
                try:
                    imodel.append(self.models[j][1](param[model][i]))
                except ValueError:
                    return -nu.inf

		#combine data with
		imodel = nu.sum(imodel,0)
        #apply multipliticave or convolution models
        for i,j in enumerate(model.split(',')):
            if j.endswith('*'):
				imodel = self.models[j][1](imodel,param[model][i])

        #make model and data have same wavelength
        
        #get likelyhood
        out = stats_dist.norm.logpdf(self.data[:,1],nu.sum(imodel,0))
        #return loglik
        return out.sum()

    def prior(self,param, model):
        '''(Example_lik_class, ndarray, str) -> float
        Calculates log-probablity for prior'''
        #return logprior
        #uniform
        out = 0
        for i,j in enumerate(model.split(',')):
            if j == 'SSP':
            #'age':
                loc = self._age_unq.min()
                scale = self._age_unq.ptp()
                out += stats_dist.uniform.logpdf(param[model][i][0],loc,scale).sum()
            #'metal':
                loc = self._metal_unq.min()
                scale = self._metal_unq.ptp()
                out += stats_dist.uniform.logpdf(param[model][i][1], loc, scale).sum()
            #'norm':
                out += stats_dist.uniform.logpdf(param[model][i][2],0,10**4).sum()
        return out
        #conj of uniform
        #stats_dist.pareto.logpdf
        #normal
        #stats_dist.norm.logpdf
        #multinormal conjuigates
        #stats_dist.gamma.logpdf
        #stats_dist.invgamma.logpdf
        #exponetal
        #stats_dist.expon
        #half normal (never negitive)
        #stats_dist.halfnorm
        


    def model_prior(self,model):
        '''(Example_lik_class, any type) -> float
        Calculates log-probablity prior for models. Not used in MCMC and
        is optional in RJMCMC.'''
        #return log_model
        return 0.

    def initalize_param(self,model):
        '''(Example_lik_class, any type) -> ndarray, ndarray

        Used to initalize all starting points for run of RJMCMC and MCMC.
        outputs starting point and starting step size'''
        if model == 'SSP':
            out_ar, outsig = nu.zeros(3), nu.identity(3)
            loc = self._age_unq.min()
            scale = self._age_unq.ptp()
            out_ar[0] =  stats_dist.uniform.rvs(loc,scale)
            #metal
            loc = self._metal_unq.min()
            scale = self._metal_unq.ptp()
            out_ar[1] = stats_dist.uniform.rvs(loc, scale)
            #normalization
            out_ar[2] =  stats_dist.uniform.rvs(0,10**4)
            return out_ar, outsig
        elif model == 'dust':
            pass
        else:
            raise KeyError("Key dosen't exsist")

        
    def step_func(self, step_crit, param, step_size, model):
        '''(Example_lik_class, float, ndarray or list, ndarray, any type) ->
        ndarray

        Evaluates step_criteria, with help of param and model and 
        changes step size during burn-in perior. Outputs new step size
        '''
        #return new_step
        if step_crit > .60:
            for i in range(len(model.split(','))):
                step_size[model][i] *= 1.05
        elif step_crit < .2:
            for i in range(len(model.split(','))):
                step_size[model][i] /= 1.05
        #cov matrix
        if len(param) % 2000 == 0:
            step_size[model] = [nu.cov(nu.asarray(param[-2000:])[:,0,:].T)]
        return step_size[model]


    def birth_death(self,birth_rate, model, param):
        '''(Example_lik_class, float, any type, rj_dict(ndarray)) -> 
           dict(ndarray), any type, bool, float

        For RJMCMC only. Does between model move. Birth rate is probablity to
        move from one model to another, models is current model and param is 
        dict of all localtions in param space. 
        Returns new param array with move updated, key for new model moving to,
        whether of not to attempt model jump (False to make run as MCMC) and the
        Jocobian for move.
        '''
        #for RJCMC
        if birth_rate > nu.random.rand():
            #birth
            #choose random model to add
            new_model = self.models.keys()[1]
            out_param = param + {new_model:[self.initalize_param(new_model)[0]]}
            new_model = out_param.keys()[0]
            
        else:
            #death
            if len(param[param.keys()[0]]) > 1:
                out_param = param - 'SSP'
                new_model = out_param.keys()[0]
            else:
                return param, model, False, 1.

        return out_param, new_model, True, 1.
        #return new_param, try_model, attemp_jump, Jocobian
        #for MCMC
        #return None, None, False, None
        
#######other functions

#used for class_map
def spawn(f):
    def fun(q_in,q_out):
        while True:
            i,x = q_in.get()
            if i == None:
                break
            q_out.put((i,f(x)))
    return fun

def parmap(f, *X):
    nprocs = multi.cpu_count()
    q_in   = multi.Queue(1)
    q_out  = multi.Queue()

    proc = [multi.Process(target=spawn(f),args=(q_in,q_out)) for _ in range(nprocs)]
    for p in proc:
        p.daemon = True
        p.start()

    sent = [q_in.put((i,x)) for i,x in enumerate(zip(*X))]
    [q_in.put((None,None)) for _ in range(nprocs)]
    res = [q_out.get() for _ in range(len(sent))]

    [p.join() for p in proc]

    return [x for i,x in sorted(res)]
