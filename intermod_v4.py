import collections
import itertools
import random


class IMD(object):
    """
    used to hold the type of IMD and it's freq value
    """
    def __init__(self, freq, imd_type):
        self.imd_type = imd_type
        self.freq = freq


class Coordination(object):
    """
    stores the existing state of the coordination
    """
    def __init__(self, start_freq=None, end_freq=None, *args, **kwargs):
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
            self.end_freq = 608
        self.imd_calc = IntermodCalculator(start_freq=self.start_freq, end_freq=self.end_freq, coordination=self)
        self.avoid_imd_thirds_by = 0.099 
        self.avoid_imd_fifths_by = 0.089
        self.avoid_imd_triples_by = 0.049
        self.default_bandwidth = 0.299
        self.all_potential_freqs = []
        self.create_potential_freqs() # just do it on class instantiation


    def create_potential_freqs(self):
        """
        this method could also watch out for DTV conflicts, and not add them to the potential list
        always reinstantiate the list for future features
        """
        self.all_potential_freqs = []
        loop_freq = self.start_freq
        while loop_freq < self.end_freq:
            self.all_potential_freqs.append(round(loop_freq, 4))
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


    def test_one_freq(self, test_freq, test=False):
        """
        returns Boolean if it meets the spec
        """
        results = True
        coordinated_freqs = self.coordinated_freqs.get_freq_values()

        # transmitter to transmitter spacing check
        for cofreq in coordinated_freqs: # test the freq spacing between all other system freqs
            if abs(test_freq-cofreq) < self.default_bandwidth:
                results = False
                return results
        # create a copy of the existing freqs and add the potential freq to it
        test_frequency_list = FrequencyList(coordinated_freqs)
        test_frequency_list.append_(test_freq)

        # calculate the imd_thirds and imd_fifths generated from this set
        imd_thirds, imd_fifths, imd_triples = self.imd_calc.calculate_imd_between_one_set_of_freqs(test_frequency_list)

        if test_freq in imd_thirds:
            results = False
        if test_freq in imd_fifths:
            results = False
        if test_freq in imd_triples:
            results = False
        else:
            # check for spacings from IMD products
            # create lists from all imd thirds and all imd fifths
            combined_thirds_list = imd_thirds+self.imd_thirds
            combined_fifths_list = imd_fifths+self.imd_fifths
            combined_triples_list = imd_triples+self.imd_triples
            """
            SOOO MANY LOOPS HERE. THIS IS INCREDIBLY INEFFICIENT
            MAKE THIS GOOD, please

            Can we make an IMD product an object with a type associated with it?
            Then we can make one list of IMD products and check the diffs based on the type
            One loop for all the IMD products, one loop for existing freqs check
            """

            for third in combined_thirds_list:
                if abs(third-test_freq) <= self.avoid_imd_thirds_by:
                    results = False
                    return results
                
            for fifth in combined_fifths_list:
                if abs(fifth-test_freq) <= self.avoid_imd_fifths_by:
                    results = False
                    return results

            for triple in combined_triples_list:
                if abs(triple-test_freq) <= self.avoid_imd_triples_by:
                    results = False
                    return results

            # if the freq passes the IMD tests, then make sure that any new generated IMD products don't interfere with existing freqs
            for f in coordinated_freqs:
                for third in combined_thirds_list:
                    if abs(third-f) <= self.avoid_imd_thirds_by: # this will find direct hits and spacing with the existing set
                        results = False
                        return results

                for fifth in combined_fifths_list:
                    if abs(fifth-f) <= self.avoid_imd_fifths_by:
                        results = False
                        return results

                for triple in combined_triples_list:
                    if abs(triple-f) <= self.avoid_imd_triples_by:
                        results = False
                        return results

            """
            END OF TERRIBLY INEFFICIENT CODE>  
            """

            if results == True:
                # at this point, we've passed all the tests, so add it the imds and coordinated freqs
                self.imd_thirds.extend(imd_thirds)
                self.imd_fifths.extend(imd_fifths)
                self.coordinated_freqs.append_(test_freq)
            else:
                self.uncoordinated_freqs.append_(test_freq)

        return results

    def run_a_test(self, start_freq=None, step_size=None):
        """
        run a test coordination:
        1 - get a random freq from the possible freqs
        2 - add freq to a temporary system and calculate IMD
        3 - evaluate whether to keep the freq or try another one happens in the method above
        """
        self.create_potential_freqs()
        while len(self.all_potential_freqs) > 0:
            freq = self.get_a_freq()
            self.test_one_freq(freq)
        return


class FrequencyList(object):
    """
    just a collection of Frequency objects
    """
    def __init__(self, list_of_freqs, *args, **kwargs):
        self.freq_list = [Frequency(f) for f in list_of_freqs]

    def __str__(self):
        return ','.join(str(f) for f in self.freq_list)

    def __repr__(self):
        return ','.join(str(f) for f in self.freq_list)
    
    def length(self):
        return len(self.freq_list)

    def append_(self, freq):
        self.freq_list.append(Frequency(freq))

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
        creats the list of pairs of Frequency objects to test for IMD
        """
        freq_list = list(itertools.combinations(self.get_freq_values(), number_of_xmitters))
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
        
        freq_list = list(itertools.combinations(combined_list, number_of_xmitters))

        return freq_list


class Frequency(object):
    """
    rather than store this as a string, store data about the freq for the coordination
    """

    def __init__(self, value, *args, **kwargs):
        self.freq = value
        self.coordinated = False

    def __str__(self):
        return str(self.freq)

    def __repr__(self):
        return str(self.freq)


class IntermodCalculator(object):
    """
    used for calculating IMD products for wireless microphone frequency selection
    frequencies are in MHz
    1 - Goal to create a list of frequencies that are spaced between the start freq and the end freq
    2 - Each frequency should be spaced at least self.spacing apart
    3 - Calculate 3rd order intermods and 5th order intermods for each possible pair of frequencies in the list and add it to the intermod lists
    4 - If any of the freqs in the intermod list are within 0.1 MHz of a frequency in the first list, move it by 0.125 and recalculate the lists
    """
    def __init__(self, start_freq=490, end_freq=500, thirds=True, fifths=True, triple_beats=True, coordination=None, **kwargs):
        self.start_freq = start_freq
        self.end_freq = end_freq
        self.thirds = thirds
        self.fifths = fifths
        self.triple_beats = triple_beats
        self.coordination = coordination # reserved for later use

    def calculate_imd_between_one_set_of_freqs(self, freqs1):
        """
        accepts a FrequencyList object and returns a two lists of IMD products
        """
        imd_thirds = []
        imd_fifths = []
        imd_triples = []
        freq_pairs = freqs1.create_freq_test_list_from_itself()
        for freq_pair in freq_pairs:
            thirds, fifths = self.calculate_imds(freq_pair[0], freq_pair[1])
            imd_thirds.extend(thirds)
            imd_fifths.extend(fifths)
        if self.triple_beats:  
            # don't waste time checking for each combo if we don't need to. There's a safety measure of checking in the calculation too
            freq_thirds = freqs1.create_freq_test_list_from_itself(3)
            for freq_combo in freq_thirds:
                f1 = freq_combo[0]
                f2 = freq_combo[1]
                f3 = freq_combo[2]
                triples = self.calculate_triple_beats(f1, f2, f3)
        return imd_thirds, imd_fifths, imd_triples
    

    def calculate_imd_between_two_sets(self, freqs1, freqs2):
        """
        freqs1 and freqs2 are FrequencyList objects.  
        rebuild to the spec in the above method
        """
        return

    def calculate_imds(self, f1, f2):
        """
        consolidates third and fifth calculation into one function
        """
        thirds = self.calculate_third_order(f1, f2)
        fifths = self.calculate_fifth_order(f1, f2)
        return thirds, fifths

    def calculate_triple_beats(self, f1, f2, f3):
        """
        F1 + F2 – F3
        F1 + F3 – F2
        F2 + F3 – F1
        """
        if self.triple_beats:
            a = f1 + f2 - f3
            b = f1 + f3 - f2
            c = f2 + f3 - f1
            # third order
            e = (2*f1) - f2
            f = (2*f2) - f1
            g = (2*f1) - f3
            h = (2*f3) - f1
            i = (2*f2) - f3
            j = (2*f3) - f2 
            # fifth order
            k = (3*f1) - (2*f2)
            l = (3*f2) - (2*f1)
            m = (3*f1) - (2*f3)
            n = (3*f3) - (2*f1)
            o = (3*f2) - (2*f3)
            p = (3*f3) - (2*f2)
            bad_freqs = set(a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p)
        return bad_freqs

    def calculate_third_order(self, f1, f2):
        """
        simply calculates the third order products
        """

        if self.thirds:
            #a = round((3*f1),3)
            #b = round((3*f2),3)
            #c = round(((2*f1)+f2),3)
            d = round(((2*f1)-f2),3)
            #e = round(((2*f2)+f1),3)
            f = round(((2*f2)-f1),3)
            bad_freqs = set(d,f)
        return bad_freqs

    def calculate_fifth_order(self, f1, f2):
        """
        
        """
        if self.fifths:
            #a = round(((3*f1)+(2*f2)),3)
            b = round(((3*f1)-(2*f2)),3)
            #c = round(((3*f2)+(2*f1)),3)
            d = round(((3*f2)-(2*f1)),3)
            bad_freqs = set(b,d)
        return bad_freqs