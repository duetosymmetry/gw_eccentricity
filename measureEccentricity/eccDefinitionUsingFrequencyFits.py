"""
Find peaks and troughs using frequency fits.

Part of Eccentricity Definition project.
Md Arif Shaikh, Mar 29, 2022
"""
from tkinter import Toplevel

from zmq import PROTOCOL_ERROR_ZMTP_MALFORMED_COMMAND_MESSAGE
from .eccDefinition import eccDefinition

import numpy as np
import scipy



class envelope_fitting_function:
    """Re-parameterize A*(t-T)^n in terms of function value, first derivative at the time t0, and T"""
    
    def __init__(self, t0, verbose=False):
        """"""
        self.t0=t0
        self.verbose=verbose


    def format(self, f0, f1, T):
        """return a string representation for use in legends and output"""
        n=-(T-self.t0)*f1/f0
        A = f0*(T-self.t0)**(-n)  
        return f"{A:.3g}(t{-T:+.2f})^{n:.3f}"


    def __call__(self, t, f0, f1, T):
        # f0, f1 are function values and first time-derivatives
        # at t0.  Re-expfress as T, n, A, then evalate A*(t-T)^n
        n=-(T-self.t0)*f1/f0
        A = f0*(T-self.t0)**(-n)
        if self.verbose:
            print(f"f0={f0}, f1={f1}, T={T}; n={n}, A={A}, max(t)={t.max()}")
        if t.max()>T:
            print(end="",flush=True)
            raise Exception("envelope_fitting_function reached parameters where merger time T is within time-series to be fitted\n"
                            f"f0={f0}, f1={f1}, T={T}; n={n}, A={A}, max(t)={max(t)}" )
        return A*(T-t)**n






class eccDefinitionUsingFrequencyFits(eccDefinition):
    """Measure eccentricity by finding extrema location using freq fits."""

    def __init__(self, *args, **kwargs):
        """Init for eccDefinitionUsingWithFrequencyFits class.

        parameters:
        ----------
        dataDict: Dictionary containing the waveform data.
        """
        super().__init__(*args, **kwargs)

        # create the shortened data-set for analysis 
        if self.extra_kwargs["num_orbits_to_exclude_before_merger"] is not None:
            merger_idx = np.argmin(np.abs(self.t))
            phase22_at_merger = self.phase22[merger_idx]
            # one orbit changes the 22 mode phase by 4 pi since
            # omega22 = 2 omega_orb
            phase22_num_orbits_earlier_than_merger = (
                phase22_at_merger
                - 4 * np.pi
                * self.extra_kwargs["num_orbits_to_exclude_before_merger"])
            idx_num_orbit_earlier_than_merger = np.argmin(np.abs(
                self.phase22 - phase22_num_orbits_earlier_than_merger))

            self.tC_analyse = self.t[:idx_num_orbit_earlier_than_merger]
            self.omega22_analyse = self.omega22[:idx_num_orbit_earlier_than_merger]
            self.phase22_analyse = self.phase22[:idx_num_orbit_earlier_than_merger]
            self.t_analyse = self.t[:idx_num_orbit_earlier_than_merger]
        else:
            self.t_analyse = self.t
            self.omega22_analyse = self.omega22
            self.phase22_analyse = self.phase22
            self.t_analyse = self.t

        # TODO - consider whether to also cut from the start (e.g. NR junk radiation)

        return

    def find_extrema(self, extrema_type="maxima"):
        """Find the extrema in the data.

        parameters:
        -----------
        extrema_type:
            One of 'maxima', 'peaks', 'minima' or 'troughs'.

        returns:
        ------
        array of positions of extrema.
        """

        # STEP 0 - setup

        if extrema_type in ['maxima', 'peaks']:
            sign=+1
        elif extrema_type in ['minima', 'troughs']:
            sign=-1
        else:
            raise Exception(f"extrema_type='{extrema_type}' unknown.")


        # data-sets to operate on (stored as member data)
        # self.t_analyse
        # self.phase22_analyse
        # self.omega22_analyse


        # DESIRED NUMBER OF EXTREMA left/right DURING FITTING
        # Code will look for N+1 extrema to the left of idx_ref, and N extrema to the right
        # TODO - make user-specifiable via option
        N = 3 

        # TODO - make verbose user-specifiable
        # TODO - better way of handling diagnostic output?
        verbose=False

        # STEP 1: 
        # global fit as initialization of envelope-subtraced extrema

        fit_center_time = 0.5*(self.t_analyse[0] + self.t_analyse[-1])
        f_fit=envelope_fitting_function(t0 = fit_center_time,
                                        verbose=False
                                        )
        # some reasonable initial guess for curve_fit
        nPN=-3./8 # the PN exponent as approximation
        f0=0.5*(self.omega22_analyse[0]+self.omega22_analyse[-1])
        p0 = [ f0,  # function value ~ omega
            -nPN*f0/(-fit_center_time),   # func = f0/t0^n*(t)^n -> dfunc/dt (t0) = n*f0/t0 
             0.   #  singularity in fit is near t=0, since waveform aligned at max(amp22)
            ]

        # some hopefully reasonable bounds for global curve_fit
        bounds0 = [[0., 0., 0.8*self.t_analyse[-1] ],
                   [1., 10./(-fit_center_time ),  -fit_center_time ]]
        
        if verbose:
            print(f"global fit: guess p0={p0}, bounds={bounds0}")
        p_global, pconv=scipy.optimize.curve_fit(f_fit, self.t_analyse, self.omega22_analyse, p0=p0, 
                        bounds=bounds0)

        # STEP 2
        # starting at start of data, move through data and do local fits across (2N+1) extrema
        # for each fit, take the middle one as part of the outptu 

        # to collect extrema
        extrema=[ ] 

        # estimates for initial start-up values (will be updated as needed)
        K = 1.2   # periastron-advance rate 
        idx_ref = np.argmax( self.phase22_analyse > self.phase22_analyse[0] + K*N*4*np.pi )
        if idx_ref == 0:
            raise Exception("data set too short.")

        p=p_global
        count=0
        while True:
            count=count+1
            if verbose:
                print(f"=== count={count} "+"="*60)
            idx_extrema,p, K, idx_ref=FindExtremaNearIdxRef(
                                self.t_analyse, self.phase22_analyse, self.omega22_analyse, 
                                idx_ref,
                                sign, N+1, N, K,
                                f_fit, p, bounds0,
                                1e-8,
                                increase_idx_ref_if_needed = True,
                                verbose=verbose)
            if verbose:
                print(f"IDX_EXTREMA={idx_extrema}, f_fit={f_fit.format(*p)}, K={K:5.3f}, idx_ref={idx_ref}")
            extrema.append(idx_extrema[N])  # use the one just to the left of idx_ref
            idx_ref = int(0.5*(idx_extrema[N+1]+idx_extrema[N+2]))
            if len(idx_extrema)<= 2*N:
                #print("WARNING - TOO FEW EXTREMA FOUND.  THIS IS LIKELY SIGNAL THAT WE ARE AT MERGER")
                break
            if count>1000: raise Exception("count large??")
        if verbose:
            print(f"Reached and of data.  Identified extrema = {extrema}")
        return np.array(extrema)

        # Procedure:
        # - find length of useable dataset
        #     - exlude from start
        #     - find Max(A) and exclude from end
        # - one global fit for initial fitting parameters
        # - check which trefs we can do:
        #     - delineate N_extrema * 0.5 orbits from start
        #     - delineate N_extrema * 0.5 orbits from end  
        #     - discard tref outside this interval (this places the trefs at least mostly into the middle of the fitting intervals. Not perfectly, since due to periastron advance the radial periods are longer than the orbital ones)
        # - set K=1
        # - set fitting_func=global_fit
        # - Loop over tref:
        #     - set old_extrema = [0.]*N_extrema
        #     - Loop over fitting-iterations:
        #         - (A) find interval that covers phase from  K*(0.5*N_extrema+0.2) orbits before to after t_ref
        #         - find extrema of omega - fit
        #         - update K based on the identified extrema
        #         - if  number of extrema != N_extrema:
        #             goto (A)  [i.e. compute a larger/smaller data-interval with new K]
        #         - if |extrema - old_extrema| < tol:  break
        #         - old_extrema=extrema
        #         - update fitting_func by fit to extrema

       




def FindExtremaNearIdxRef(t, phase22, omega22, 
                          idx_ref,
                          sign, Nbefore, Nafter, K,
                          f_fit, p_initial, bounds,
                          TOL,
                          increase_idx_ref_if_needed = True,
                          verbose=False):
    """given a 22-GW mode (t, phase22, omega22), identify a stretch of data [idx_lo, idx_hi]
    centered roughly around the index idx_ref which satisfies the following properties:
      - The interval [idx_lo, idx_hi] contains Nbefore+Nafter maxima (if sign==+1) or minimia (if sign==-1)
        of trend-subtracted omega22, where Nbefore exrema are before idx_ref and Nafter extrema are after idx_ref
      - The trend-subtraction is specified by the fitting function omega22_trend = f_fit(t, *p).
        Its fitting parameters *p are self-consistently fitted to the N_extrema extrema.  
      - if increase_idx_ref_if_needed, idx_ref is allowed to increase in order to reach the desired Nbefore.

    INPUT
      - t, phase22, omega22 -- data to analyse
      - idx_ref   - the reference index, i.e. the approximate middle of the interval of data to be sought
      - sign      - if +1, look for maxima, if -1, look for minima
      - Nbefore   - number of extrema to identify before idx_ref
      - Nafter    - number of extrema to identify after idx_ref 
                      if Nafter=Nbefore-1, then the Nbefore'th extremum will be centered
      - K         - an estimate for the periastron advance of the binary, i.e. the increase of phase22/4pi between two extrema
      - f_fit     - fitting function f_fit(t, *p) to use for trend-subtraction
      - p_initial - initial guesses for the best-fit parametes
      - p_bounds  - bounds for the best-fit parameters
      - TOL       - iterate until the maximum change in any one omega at an extremum is less tha this TOL
      - increase_idx_ref_if_needed -- if true, allows to increase idx_ref in order to achieve Nbefore extrema between
                                      start of dataset and idx_ref (idx_ref will never be decreased, in order to preserve
                                      monotonicity to help tracing out an inspiral)


    RETURNS:
          idx_extrema, p, K, idx_ref
    where
      - idx_extrema -- the indices of the identified extrema
                       USUALLY len(idx_extrema) == Nbefore+Nafter
                       HOWEVER, if Nafer cannot be reached because of end-of-data, then 
                         a) if one extremum too few is identified, returns idx_extrema of length Nbefore+Nafter-1
                         b) if two or more extrema too few are identified, then raise Exception

      - p -- the fitting parameters of the best fit through the extrema
      - K -- an updated estimate of the periastron advance K (i.e. the average increase of phase22 between 
             extrema divided by 4pi)
      - idx_ref -- a (potentially increased) value of idx_ref, so that Nbefore extrema were found between the
                   start of the data and idx_ref


    ASSUMPTIONS & POSSIBLE FAILURE MODES
      - if increase_idx_ref_if_needed == False, and idx_lo cannot be reduced enough to reach Nbefore 
          -> raise Exception 
      - if identified number of maxima after is exactly **ONE** below the target Nafter
          -> return normally, but with len(idx_extrema) **ONE SHORTER** than Nbefore+Nafter
             This signals that the end of the data is reached, and that the user should not 
             press to even larger idx_ref.
      - if identified number of maxima after is **two** or more below the target Nafter
          -> raise Exception

    """
    if verbose:
        print(f"FindExtremaNearIdxRef  idx_ref={idx_ref}, K_initial={K:5.3f}, p_initial={f_fit.format(*p_initial)}")

    DeltaPhase = 4*np.pi*K  # look for somewhat more data than we (probably) need
    idx_lo = np.argmax( phase22 > phase22[idx_ref] - DeltaPhase*Nbefore)
    idx_hi = np.argmax( phase22 > phase22[idx_ref] + DeltaPhase*Nafter)
    if idx_hi == 0:
        idx_hi=len(phase22)
        if verbose:
            print("WARNING: reaching end of data, so close to merger")
    p = p_initial
    it=0

    old_extrema = np.zeros(Nbefore+Nafter)
    old_idx_lo, old_idx_hi = -1, -1
    while True:
        it=it+1

        if it>10: 
            raise Exception("FindExtremaNearIdxRef seems to not converge (use 'verbose=True' to diagnose)")

        if verbose:
            print(f"it={it}:  [{idx_lo} / {idx_ref} / {idx_hi}]")
        omega_residual = omega22[idx_lo:idx_hi] - f_fit(t[idx_lo:idx_hi], *p)

        # TODO -- pass user-specified arguments into find_peaks      
        # POSSIBLE UPGRADE 
        # find_peaks on discrete data will not identify a peak to a location better than the
        # time-spacing.  To improve, one can add a parabolic fit to the data around the time
        # of extremum, and then take the (fractional) index where the fit reaches its maximum.
        # Harald has some code to do this, but he hasn't moved it over yet to keep the base-
        # implementation simple. 
        idx_extrema,properties=scipy.signal.find_peaks(sign*omega_residual
                                                         #width=10,
                                                         # prominence=omega_residual_amp*0.03,width=10
                                                        )
        idx_extrema=idx_extrema+idx_lo # add offset due to to calling find_peaks with sliced data
        Nleft=sum(idx_extrema<idx_ref)
        Nright=sum(idx_extrema>=idx_ref)

        # update K based on identified peaks
        K = (phase22[idx_extrema[-1]] - phase22[idx_extrema[0]]) / (4*np.pi * (len(idx_extrema)-1 ))
        if verbose:
            print(f"    : idx_extrema={idx_extrema}, Nleft={Nleft}, Nright={Nright}, K={K:5.3f}")

        if Nleft != Nbefore or Nright!=Nafter:
            # number of extrema not as we wished, so update [idx_lo, idx_hi]
            if Nleft>Nbefore: # too many peaks left, discard by placing idx_lo between N and N+1's peak to left
                idx_lo = int((idx_extrema[Nleft-Nbefore-1]+idx_extrema[Nleft-Nbefore])/2) 
                if verbose:
                    print(f"    : idx_lo increased to {idx_lo}")
            elif Nleft<Nbefore: # reduce idx_lo to capture one more peak

                if idx_lo==0:
                    # no more data to the left, so consider shifting idx_ref
                    if increase_idx_ref_if_needed:
                        if Nright>=2:
                            # we need at least two maxima to the right to average for the new idx_ref
                            tmp=np.argmax(idx_extrema >= idx_ref)
                            # shift idx_ref one extremum to the right
                            idx_ref = int((idx_extrema[tmp] + idx_extrema[tmp+1])/2)

                            Nright=Nright-1 # reflect the change in idx_ref to aid in updating idx_hi
                            if verbose:
                                print(f"    : idx_ref increased to {idx_ref}")
                        else:
                            pass 
                            # First, wait for the idx_hi-updating below to widen the interval.
                            # The next iteration will come back here and update idx_ref

                    else:
                        raise Exception(f"could not identify {Nbefore} extrema to the left of idx_ref={idx_ref}")
                else:
                    # target phase on left 1.5 radial periods before first identified peak
                    # that should conveniently cover the next earlier peak.  If there's not enough
                    # data then this search returns the first data-point
                    phase_lo = phase22[idx_extrema[0]] - K*4*np.pi*1.5   
                    idx_lo =  np.argmax( phase22 > phase_lo )
                    if verbose:
                        print(f"    : idx_lo reduced to {idx_lo}")

            if Nright>Nafter: # too many peaks to the right right, discard by placing idx_hi between N and N+1's peak to right
                idx_hi = int((idx_extrema[Nafter-Nright]+idx_extrema[Nafter-Nright-1])/2) 
                if verbose:
                    print(f"    : idx_hi reduced to {idx_hi}")
            elif Nright<Nafter: # increase idx_hi to capture one more peak

                # do we have extra data?
                if idx_hi<len(phase22):
                    # target phase on right 1.5 radial periods after last identified peak
                    phase_hi = phase22[idx_extrema[-1]] + K*4*np.pi*1.5   
                    idx_hi = np.argmax( phase22 > phase_hi )
                    if idx_hi==0:  
                        # coulnd't get as much data as we wished, take all we have
                        idx_hi=len(phase22)  
                    if verbose:
                        print(f"    : idx_hi increased to {idx_hi}")
                else:
                    # we had already fully extended idx_hi in earlier iteration
                    if Nright<Nafter-1:
                        # data-set at least *two* extrema too short

                        if (idx_lo,idx_hi)!=(old_idx_lo, old_idx_hi) \
                            or it <= interval_changed_on_it+1:
                            # we just changed the interval, or didn't yet have 
                            # the extra iteration that does perform a new curve_fit
                            # therefore, continue to do another curve_fit, in the hopes
                            # that it might identify one more extremum
                            pass
                        else:
                            # sorry - don't know what else to do
                            raise Exception(f"data set *two* or more extrema too short after idx_ref={idx_ref}.")
                    else:
                        # data set only one extrema to the right too short, perform
                        # fit, and use the fact that the returned number of extrema
                        # is too few to signal end-of-data
                        pass
                    if verbose:
                        print(f"    : idx_hi at its maximum, but still insufficient Nright={Nright}")

            if (idx_lo,idx_hi) != (old_idx_lo, old_idx_hi):
                interval_changed_on_it=it  # remember when we last changed the search interval
                (old_idx_lo, old_idx_hi)  = (idx_lo, idx_hi)
                # data-interval was updated; go back to start of loop to re-identify extrema
                continue 

        # if the code gets here, it has identified [idx_lo, idx_high] with the
        # right number of envelope-subtracted extrema.
        # 
        # Now check whether omega-envelope fitting has already converged.  
        # If yes: return
        # If no:  re-fit envelope

        omega22_extrema = omega22[idx_extrema]
        if len(omega22_extrema) != len(old_extrema):  # number of extrema can change near merger
            max_delta_omega=1e99
        else:
            max_delta_omega = max(np.abs(omega22_extrema-old_extrema))

        if max_delta_omega< TOL:
            # (this cannot trigger on first iteration, due to initialization of old_extrema)
            if verbose:
                print(f"    : extrema & omega(extrema) unchanged.  Done")
            return idx_extrema, p, K, idx_ref

        # not done, update fit 
        p, pconv=scipy.optimize.curve_fit(f_fit, t[idx_extrema], omega22[idx_extrema], p0=p, 
                                            bounds=bounds)
        old_extrema=omega22_extrema
        if verbose:
            print(f"    : max_delta_omega={max_delta_omega:5.4g} => fit updated to f_fit={f_fit.format(*p)}")
        if(it>100): raise Exception("FindExtremaNearIdxRef did not converge")

    raise Exception("Should never get here")
        
