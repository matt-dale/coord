import collections
import itertools
import random
import numpy as np

"""
for profiling, keep the same set of variables, start=470, stop = 500, and don't calculate triple_beats
v4 found instantiating IMD as an object for all the 5million IMD products is a time waster.
v5, remove that class creation and use three seperate loops saved tons of time
v6, adding in the check on self.coordinated freqs spacing against the IMD products, notably increase in time. 
v7, removing round from all locations and changing abs to local in the function - very little change

added Numpy arrays in V11, no change in speed, but wasn't able to lose all for loops.
V12 increased speed by adding more math to the np arrays in the test_one_freq method
reduced calc time to 9 seconds for full IMD checks and 2.78 secs for 3rd/5th imd checks

V13 adding in Equipment models to check spacings against
"""

class Coordination(object):
    """
    stores the existing state of the coordination
    """
    def __init__(self, start_freq=None, end_freq=None, thirds=True, fifths=True, triples=True, freqs_to_avoid=[], *args, **kwargs):
        self.coordinated_freqs = FrequencyList([])
        self.uncoordinated_freqs = FrequencyList([])
        self.imd_thirds = []
        self.imd_fifths = []
        self.imd_triples = []
        if start_freq:
            self.start_freq = start_freq
        else:
            self.start_freq = 470
        if end_freq:
            self.end_freq = end_freq
        else:
            self.end_freq = 608 # 608 is a reasonable ending

        self.thirds = thirds
        self.fifths = fifths
        self.triple_beats = triples
        self.imd_calc = IntermodCalculator(start_freq=self.start_freq, 
                                            end_freq=self.end_freq, thirds=self.thirds, 
                                            fifths=self.fifths, triple_beats=self.triple_beats, 
                                            coordination=self)
        self.avoid_imd_thirds_by = 0.099 
        self.avoid_imd_fifths_by = 0.089
        self.avoid_imd_triples_by = 0.049
        self.default_bandwidth = 0.299
        self.freqs_to_avoid = freqs_to_avoid # this is a list of frequencies that should be avoided by x spacing.  
        # Should we care about what they are (DTV vs. IEM vs. mic)?  They should still be included in the IMD tests
        self.all_potential_freqs = []
        self.current_model = None
        self.create_potential_freqs()

    def create_file_for_IAS_import(self):
        with open('exported_freqs.csv', 'w') as outFile:
            h = ','.join([str(x) for x in self.coordinated_freqs.get_freq_values()])
            outFile.write(h+'\r\n')

    def accept_equipment_model(self, equipment_model):
        """
        unpacks the model's attrs onto self
        """
        if not equipment_model:
            model = EquipmentModel() # use defaults
        else:
            model = equipment_model

        # set these params based on the model
        self.default_bandwidth = model.bandwidth
        self.thirds = model.imd_thirds
        self.fifths = model.imd_fifths
        self.triple_beats = model.imd_triple_beats
        self.start_freq = model.start_freq
        self.end_freq = model.end_freq

        # now recreate imd calc since things have changed
        self.imd_calc = IntermodCalculator(start_freq=self.start_freq, 
                                    end_freq=self.end_freq, thirds=self.thirds, 
                                    fifths=self.fifths, triple_beats=self.triple_beats, 
                                    coordination=self)

        # also set current model for everyone else
        self.current_model = model
        return

    def create_potential_freqs(self):
        """
        this method could also watch out for DTV conflicts, and not add them to the potential list
        always reinstantiate the list for future features
        """
        self.all_potential_freqs = []
        loop_freq = self.start_freq
        avoidance_freqs =  self.coordinated_freqs.get_freq_values() 
        avoidance_freqs.extend(self.freqs_to_avoid)
        while loop_freq < self.end_freq:
            if loop_freq not in avoidance_freqs:
                self.all_potential_freqs.append(loop_freq)
            loop_freq += 0.025
        return

    def get_a_freq(self):
        """
        pick a random freq from the list of potentials
        """
        if len(self.all_potential_freqs) > 0:
            freq = random.choice(self.all_potential_freqs)
            self.all_potential_freqs.remove(freq)
            return freq
        else:
            raise ValueError('potential freqs have not been populated yet, this has been run out of order')


    def test_one_freq(self, test_freq):
        """
        returns Boolean if it meets the spec
        return out early if at all possible to save times
        """

        results = True
        coordinated_freqs = self.coordinated_freqs.get_freq_values()

        # search for direct hits first to avoid calculating unneccessary imds
        if test_freq in self.imd_thirds:
            return False
        if test_freq in self.imd_fifths:
            return False
        if test_freq in self.imd_triples:
            return False

        # transmitter to transmitter spacing check
        for cofreq in coordinated_freqs: # test the freq spacing between all other system freqs
            if abs(test_freq-cofreq) < self.default_bandwidth:
                results = False
                return results


        test_frequency_list = FrequencyList(coordinated_freqs, added_freq=test_freq)
        xmit_qty = 2
        if self.triple_beats:
            xmit_qty = 3
        test_list = test_frequency_list.create_freq_test_list_from_itself(xmit_qty)
        imd_thirds, imd_fifths, imd_triples = self.imd_calc.calculate_imd_between_one_set_of_freqs(test_list)


        if test_freq in imd_thirds:
            return False
        if test_freq in imd_fifths:
            return False
        if test_freq in imd_triples:
            return False
        else:
            # check for spacings from IMD products
            # create lists from all imd thirds and all imd fifths
            combined_thirds_list = list(imd_thirds)+self.imd_thirds
            combined_fifths_list = list(imd_fifths)+self.imd_fifths
            combined_triples_list = list(imd_triples)+self.imd_triples
            list_comparison = [len(combined_thirds_list), len(combined_fifths_list), len(combined_triples_list)]
            array_length = max(list_comparison)

            # lists need to be the same size
            if list_comparison[0] < array_length: # thirds
                combined_thirds_list.extend([0 for x in range(array_length-list_comparison[0])])
            if list_comparison[1] < array_length:
                combined_fifths_list.extend([0 for x in range(array_length-list_comparison[1])])
            if list_comparison[2] < array_length:
                combined_triples_list.extend([0 for x in range(array_length-list_comparison[2])])
            np_imds = np.array([combined_thirds_list, combined_fifths_list, combined_triples_list])
            differences = np_imds - test_freq
            results3 = abs(differences[0]) <= self.avoid_imd_thirds_by
            results5 = abs(differences[1]) <= self.avoid_imd_fifths_by
            results_triple = abs(differences[2]) <= self.avoid_imd_triples_by
            if results3.any() or results5.any() or results_triple.any():
                self.uncoordinated_freqs.append_(test_freq)
                return False

                
            for f in coordinated_freqs:
                f_difference = abs(np_imds[0]-f)
                if (f_difference <= self.avoid_imd_thirds_by).any():
                    self.uncoordinated_freqs.append_(test_freq)
                    return False
                f_difference = abs(np_imds[1]-f)
                if (f_difference <= self.avoid_imd_thirds_by).any():
                    self.uncoordinated_freqs.append_(test_freq)
                    return False
                if self.triple_beats:
                    f_difference = abs(np_imds[2]-f)
                    if (f_difference <= self.avoid_imd_thirds_by).any():
                        self.uncoordinated_freqs.append_(test_freq)
                        return False

        if results == True:
            # at this point, we've passed all the tests, so add the imds and coordinated freqs
            self.imd_thirds.extend(imd_thirds)
            self.imd_fifths.extend(imd_fifths)
            self.imd_triples.extend(imd_triples)
            self.coordinated_freqs.append_(test_freq, model=self.current_model) # needs to include model, V13
        else:
            self.uncoordinated_freqs.append_(test_freq, model=self.current_model)

        return results

    def calculate(self, equipment_model=None, start_freq=None, end_freq=None, test_freqs=None):
        """
        run a test coordination:
        1 - get a random freq from the possible freqs
        2 - add freq to a temporary system and calculate IMD
        3 - evaluate whether to keep the freq or try another one happens in the method above
        """
        self.accept_equipment_model(equipment_model) # changes all the default settings to those supplied by the model
        # allow per test overriding of the model start and end freqs
        if start_freq:
            self.start_freq = start_freq
        if end_freq:
            self.end_freq = end_freq
        # potential issue here if there are test_freqs outside the band of the current model. what is expected?
        if test_freqs:
            self.all_potential_freqs = test_freqs
        else:
            self.create_potential_freqs()
        while len(self.all_potential_freqs) > 0:
            freq = self.get_a_freq()
            self.test_one_freq(freq)
        return





class FrequencyList(object):
    """
    just a collection of Frequency objects
    """
    def __init__(self, list_of_freqs, added_freq=None, *args, **kwargs):
        self.freq_list = [Frequency(f) for f in list_of_freqs]
        self.added_freq = added_freq

    def __str__(self):
        return ','.join(str(f) for f in self.freq_list)

    def __repr__(self):
        return ','.join(str(f) for f in self.freq_list)
    
    def length(self):
        return len(self.freq_list)

    def append_(self, freq, model=None):
        self.freq_list.append(Frequency(freq, model=model))

    def extend(self, freq_list):
        if type(freq_list) == FrequencyList:
            self.freq_list.extend(freq_list.get_freq_values())
        else:
            for f in freq_list:
                self.append_(f)

    def get_freq_values(self):
        return [f.freq for f in self.freq_list]

    def create_freq_test_list_from_itself(self, number_of_xmitters=2):
        """
        creates the list of pairs of Frequency objects to test for IMD
        """
        if self.added_freq:
            if number_of_xmitters == 2:
                freq_list = [(self.added_freq, f) for f in self.get_freq_values()]
            if number_of_xmitters == 3:
                two_xmit_list = itertools.combinations(self.get_freq_values(), 2) # all existing 2Xmit combos, now add the new freq to it
                freq_list = [(self.added_freq, f[0], f[1]) for f in two_xmit_list]
        else:
            freq_list = itertools.combinations(self.get_freq_values(), number_of_xmitters)
        return freq_list

    def create_freq_test_list_from_another_list(self, another_list, number_of_xmitters=2):
        """
        creates a list of freq values based on the given freq list
        the result should be each possible unique combination of two frequencies, one from self and another from another list
        """
        if type(another_list) == FrequencyList:
            combined_list = self.get_freq_values() + another_list.get_freq_values()
        elif type(another_list) == list:
            combined_list = self.get_freq_values() + another_list
        else:
            raise TypeError('Wrong type of list provided to create a new frequency list.')
        
        freq_list = itertools.combinations(combined_list, number_of_xmitters)

        return freq_list


class Frequency(object):
    """
    rather than store this as a string, store data about the freq for the coordination
    future features will need this
    """

    def __init__(self, value, model=None, *args, **kwargs):
        self.freq = value
        self.coordinated = False
        self.model = model

    def __str__(self):
        return str(self.freq)

    def __repr__(self):
        return str(self.freq)


class IntermodCalculator(object):
    """
    used for calculating IMD products for wireless microphone frequency selection
    frequencies are in MHz
    """
    def __init__(self, start_freq=490, end_freq=500, thirds=True, fifths=True, triple_beats=True, coordination=None, **kwargs):
        self.start_freq = start_freq
        self.end_freq = end_freq
        self.thirds = thirds
        self.fifths = fifths
        self.triple_beats = triple_beats
        self.coordination = coordination # reserved for later use

    def calculate_imd_between_one_set_of_freqs_numpy(self, test_freqs):
        """
        accepts a list of two or three frequency combinations and returns a two lists of IMD products
        """
        imd_thirds = set()
        imd_fifths = set()
        imd_triples = set()
        for freq_set in test_freqs:
            f1 = freq_set[0]
            f2 = freq_set[1]
            if self.triple_beats:
                f3 = freq_set[2]
                _imd_thirds, _imd_fifths, _imd_triples = self.calculate_three_transmitter_imds(f1,f2,f3)
                imd_triples.update(_imd_triples)
            else:
                _imd_thirds, _imd_fifths, _imd_triples = self.calculate_two_transmitter_imds(f1, f2)
            imd_thirds.update(_imd_thirds)
            imd_fifths.update(_imd_fifths)
        return imd_thirds, imd_fifths, imd_triples

    def calculate_imd_between_one_set_of_freqs(self, test_freqs):
        """
        accepts a list of two or three frequency combinations and returns a two lists of IMD products
        """
        imd_thirds = set()
        imd_fifths = set()
        imd_triples = set()
        for freq_set in test_freqs:
            f1 = freq_set[0]
            f2 = freq_set[1]
            if self.triple_beats:
                f3 = freq_set[2]
                _imd_thirds, _imd_fifths, _imd_triples = self.calculate_three_transmitter_imds(f1,f2,f3)
                imd_triples.update(_imd_triples)
            else:
                _imd_thirds, _imd_fifths, _imd_triples = self.calculate_two_transmitter_imds(f1, f2)
            imd_thirds.update(_imd_thirds)
            imd_fifths.update(_imd_fifths)
        return imd_thirds, imd_fifths, imd_triples
    

    def calculate_imd_between_two_sets(self, freqs1, freqs2):
        """
        freqs1 and freqs2 are FrequencyList objects.  
        this should be used to check existing system with new potentials
        """
        return

    def calculate_three_transmitter_imds(self, f1, f2, f3):
        """
        returns sets of calculated freqs
        """
        imd_thirds = set()
        imd_fifths = set()
        imd_triples = set()
        if self.triple_beats:
            a = f1 + f2 - f3
            b = f1 + f3 - f2
            c = f2 + f3 - f1
            imd_triples.update([a,b,c])
        if self.thirds:
            # third order
            e = (2*f1) - f2
            f = (2*f2) - f1
            g = (2*f1) - f3
            h = (2*f3) - f1
            i = (2*f2) - f3
            j = (2*f3) - f2 
            imd_thirds.update([e,f,g,h,i,j])
        if self.fifths:
            # fifth order
            k = (3*f1) - (2*f2)
            l = (3*f2) - (2*f1)
            m = (3*f1) - (2*f3)
            n = (3*f3) - (2*f1)
            o = (3*f2) - (2*f3)
            p = (3*f3) - (2*f2)
            imd_fifths.update([k,l,m,n,o,p])
        return imd_thirds, imd_fifths, imd_triples

    def calculate_two_transmitter_imds(self, f1, f2):
        """
        simply calculates the third order products
        """
        imd_thirds = set()
        imd_fifths = set()
        imd_triples = set() # never gets filled, just return it for consistency
        if self.thirds:
            #thirds
            d = (2*f1)-f2
            f = (2*f2)-f1
            imd_thirds.update([d,f])
            #fifths
            b = (3*f1)-(2*f2)
            d = (3*f2)-(2*f1)
            imd_fifths.update([b,d])
        return imd_thirds, imd_fifths, imd_triples


class EquipmentModel(object):
    """
    holds default values for imd calculator
    """
    def __init__(self, 
                manufacturer='Generic', 
                model='Generic',
                range_name='Generic',
                start_freq=470,
                end_freq=608,
                no_of_presets=0,
                vhf_or_uhf='UHF',
                bandwidth=0.299,
                imd_thirds=True,
                imd_fifths=True,
                imd_triple_beats=True,
                *args, **kwargs):
        self.manufacturer = manufacturer
        self.model = model
        self.range_name	= range_name
        self.start_freq	= start_freq
        self.end_freq = end_freq
        self.no_of_presets = no_of_presets
        self.vhf_or_uhf = vhf_or_uhf
        self.bandwidth = bandwidth
        self.imd_thirds = imd_thirds
        self.imd_triple_beats = imd_triple_beats
        self.imd_fifths = imd_fifths
