import itertools

class Coordination(object):
    """
    stores the existing state of the coordination
    """
    def __init__(self, *args, **kwargs):
        self.coordinated_freqs = FrequencyList([])
        self.uncoordinated_freqs = FrequencyList([])
        self.band = 'UHF'
        self.low_stop = 50
        self.high_stop = 950
        self.imd_thirds = []
        self.imd_fifths = []
        self.imd_calc = IntermodCalculator(start_freq=470, end_freq=615, coordination=self)
        self.avoid_imd_thirds_by = 0.099 
        self.avoid_imd_fifths_by = 0.089
        self.default_bandwidth = 0.299

    def run_a_test(self):
        """
        run a test coordination:
        1 - get a list of freqs that we'd like to test from the imd_calc
        2 - add two freqs from the list to the test list and calculate IMD
        3 - evaluate whether to keep the freq or try another one 
        IAS says that only 8 of these freqs are coordinated: 494.750 is not because of IMD 5ths?

        490, 490.375, 491.375, 491.75, 493.75, 494.75, 495.5, 496.5, 498.75
        """
        test_frequencies = self.imd_calc.get_freqs()
        uncoordinated_freqs = self.uncoordinated_freqs.get_freq_values() # these are freqs that we've already tested
        for freq in test_frequencies:
            # bail out early if there is a direct hit with any of the IMDs
            if freq in self.imd_thirds or freq in self.imd_fifths:
                continue
            elif freq in uncoordinated_freqs: #we've already tested this one
                continue
            elif self.coordinated_freqs.length() == 0:
                # if there are no freqs to test against, then just assume it's ok 
                # TODO:  check against known DTV and any supplied freqs
                self.coordinated_freqs.append_(freq)
            else:
                # test this freq against all others in the coordinated list
                # create a copy of the existing coordinated_freqs and add the test freq to it 
                test_list = FrequencyList(self.coordinated_freqs.get_freq_values())
                test_list.append_(freq)
                thirds, fifths = self.imd_calc.calculate_imd_between_one_set_of_freqs(test_list)
                if self.test_one_freq(freq, thirds, fifths):
                    # if the freq passes the IMD tests, then add it to coordinated_freqs and add all the IMDs to the respective lists
                    self.coordinated_freqs.append_(freq)
                    self.imd_thirds.append(thirds)
                    self.imd_fifths.append(fifths)
                else:
                    # if it doesn't pass the test, just add the freq to uncoordinated_freqs
                    self.uncoordinated_freqs.append_(freq)

    def test_one_freq(self, freq, imd_thirds, imd_fifths):
        """
        returns Boolean if it meets the spec
        """
        results = True
        #low_end = freq - self.default_bandwidth/2
        #high_end = freq + self.default_bandwidth/2
        for cofreq in self.coordinated_freqs.get_freq_values(): # test the freq spacing between all other system freqs
            if abs(freq-cofreq) < self.default_bandwidth:
                results = False
                return results

        if freq in imd_thirds:
            results = False
        elif freq in imd_fifths:
            results = False
        else:
            #check for spacings from IMD products
            for third in imd_thirds:
                if abs(third-freq) <= self.avoid_imd_thirds_by:
                    results = False
                    return results
                """
                if abs(third-low_end) <= self.avoid_imd_thirds_by:
                    results = False
                    return results
                if abs(third-high_end) <= self.avoid_imd_thirds_by:
                    results = False
                    return results
                """
            for fifth in imd_fifths:
                if abs(fifth-freq) <= self.avoid_imd_fifths_by:
                    results = False
                    return results
                """
                if abs(fifth-low_end) <= self.avoid_imd_fifths_by:
                    results = False
                    return results
                if abs(fifth-high_end) <= self.avoid_imd_fifths_by:
                    results = False
                    return results
                """

        return results



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

    def create_freq_pair_list_from_itself(self):
        """
        creats the list of pairs of Frequency objects to test for IMD
        """
        freq_list = list(itertools.combinations(self.freq_list, 2))
        return freq_list

    def create_freq_pair_list_from_another_list(self, another_list):
        """
        creates a list of freq values based on the given freq list
        the result should be each possible unique combination of two frequencies, one from self and another from another list
        """
        pair_list = []
        # which list is larger? That one should be the base loop
        if len(self.freq_list) <= len(another_list.freq_list): # doesn't matter which is which if they are the same length
            main_loop_list = another_list.freq_list
            sub_loop_list = self.freq_list
        else:
            main_loop_list = self.freq_list
            sub_loop_list = another_list.freq_list

        for freq in main_loop_list:
            this_pair = []
            for sub_freq in sub_loop_list:
                this_pair.append([freq, sub_freq])
            pair_list.append(this_pair)
        return pair_list


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
    def __init__(self, start_freq=490, end_freq=500, thirds=True, fifths=True, coordination=None, **kwargs):
        self.start_freq = start_freq
        self.end_freq = end_freq
        self.thirds = thirds
        self.fifths = fifths
        self.spacing = 0.125
        self.coordination = coordination # reserved for later use
        if self.coordination:
            self.low_stop = coordination.low_stop
            self.high_stop = coordination.high_stop

    def get_freqs(self, start_freq=None):
        """
        This function *SHOULD* return a "pre-coordinated" list of freqs, 
        NOT evenly spaced.  But how?
        returns evenly spaced frequencies in a list format
        # TODO: after a search fails, provide with a start_freq, offsetted by X amount
        to find more freqs
        """
        freqs = []
        if start_freq:
            current_freq = start_freq
        else:
            current_freq = self.start_freq
        while current_freq < self.end_freq:
            freqs.append(current_freq)
            current_freq += self.spacing
        return freqs

    def calculate_imd_between_one_set_of_freqs(self, freqs1):
        """
        accepts a FrequencyList object and returns a two lists of IMD products
        """
        imd_thirds = []
        imd_fifths = []
        freqs_to_test = freqs1.create_freq_pair_list_from_itself()
        for freq_pair in freqs_to_test:
            thirds, fifths = self.calculate_imds(freq_pair[0].freq, freq_pair[1].freq)
            imd_thirds.extend(thirds)
            imd_fifths.extend(fifths)

        return imd_thirds, imd_fifths
    

    def calculate_imd_between_two_sets(self, freqs1, freqs2):
        """
        freqs1 and freqs2 are FrequencyList objects.  
        """
        pair_list = freqs1.create_freq_pair_list_from_another_list(freqs2) 
        # lists of Frequency objects so we can store other information on the Frequency object
        imds = []
        for freq_lists in pair_list:
            for freq_pair in freq_lists:
                f1 = freq_pair[0]
                f2 = freq_pair[1]
                third_imds = self.calculate_third_order(f1.freq, f2.freq)
                fifth_imds = self.calculate_fifth_order(f1.freq, f2.freq)
                if len(third_imds):
                    # do something here to freq?
                    imds.extend(third_imds)
                if len(fifth_imds):
                    imds.extend(fifth_imds)
        return imds

    def calculate_imds(self, f1, f2):
        """
        consolidates third and fifth calculation into one function
        """
        thirds = self.calculate_third_order(f1, f2)
        fifths = self.calculate_fifth_order(f1, f2)
        return thirds, fifths

    def calculate_third_order(self, f1, f2):
        """
        simply calculates the third order products
        """
        bad_freqs = []
        if self.thirds:
            #a = round((3*f1),3)
            #b = round((3*f2),3)
            #c = round(((2*f1)+f2),3)
            d = round(((2*f1)-f2),3)
            #e = round(((2*f2)+f1),3)
            f = round(((2*f2)-f1),3)
            
            for x in [d,f]:
                #if x > self. and x < self.end_freq:
                bad_freqs.append(x)
        return set(bad_freqs)

    def calculate_fifth_order(self, f1, f2):
        """
        
        """
        bad_freqs = []
        if self.fifths:
            #a = round(((3*f1)+(2*f2)),3)
            b = round(((3*f1)-(2*f2)),3)
            #c = round(((3*f2)+(2*f1)),3)
            d = round(((3*f2)-(2*f1)),3)
            for x in [b,d]:
                #if x > self.start_freq and x < self.end_freq:
                bad_freqs.append(x)
        return set(bad_freqs)
