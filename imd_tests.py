import unittest
from intermod_v3 import IntermodCalculator, FrequencyList, Coordination

"""
# Simplest IMD calculator stories
# All frequencies are spec'd in MHz

1 - Calculate the imd products of two distinct frequencies for third order and fifth order products.  Return frequencies inside the start and end window
2 - Get a list of frequencies inside a start and end window conforming to the following guidelines: 
    - spacing between channels should be at a minimum {{spacing}} apart with a default of 0.125
3 - Tests a given freq against a list of existing freqs and IMD products to make sure it does not conflict.
4 - Get a list of frequencies that conform to step 2, but also is NOT within {{spacing}} of any possible IMD product
"""

class TestIMDCalculator(unittest.TestCase):
    
    def test_story_1_thirds(self):
        imd = IntermodCalculator(start_freq=490,end_freq=600)
        f1 = 525
        f2 = 525.125
        third_order = imd.calculate_third_order(f1, f2)
        result_thirds = set([524.875, 525.25])
        self.assertEqual(third_order, result_thirds)
        for freq in third_order:
            self.assertGreaterEqual(freq, imd.start_freq)
            self.assertLessEqual(freq, imd.end_freq)

    def test_story_1_fifths(self):
        imd = IntermodCalculator(start_freq=490,end_freq=600)
        f1 = 525
        f2 = 525.125
        fifth_order = imd.calculate_fifth_order(f1,f2)
        result_fifths = set([524.75,525.375])
        self.assertEqual(fifth_order, result_fifths)
        for freq in fifth_order:
            self.assertGreaterEqual(freq, imd.start_freq)
            self.assertLessEqual(freq, imd.end_freq)

    def test_story_2_part1(self):
        imd = IntermodCalculator(start_freq=490,end_freq=600)
        freqs = imd.get_freqs()
        self.assertGreater(len(freqs), 0) # make sure something is in the result
        
    def test_story_2_part2(self):
        imd = IntermodCalculator(start_freq=490, end_freq=600)
        freqs = set(imd.get_freqs()) # get them in order if they aren't
        last_freq = None # we already know something is in the result from the test above
        for f in freqs:
            if last_freq == None:
                continue
            else:
                self.assertGreaterEqual(f-last_freq, imd.spacing)
                last_freq = f

    def test_story_3_freq_list_creation(self):
        imd = IntermodCalculator(start_freq=490, end_freq=600)
        existing_freqs = [490, 491.5, 492.55, 493.325]
        freq_list1 = FrequencyList(existing_freqs)
        self.assertEqual(len(freq_list1.freq_list),len(existing_freqs))

    def test_story_3_freq_list_pair_creation(self):
        imd = IntermodCalculator(start_freq=490, end_freq=600)
        existing_freqs = [490, 491.5, 492.55, 493.325]
        freq_list1 = FrequencyList(existing_freqs)
        # by using same values for each list, we know the output and order
        second_freq_list = [490, 491.5, 492.55, 493.325] 
        freq_list2 = FrequencyList(second_freq_list)
        # create pair list for IMD calculation
        pair_list = freq_list1.create_freq_pair_list_from_another_list(freq_list2)
        first_pair = [existing_freqs[0], second_freq_list[0]]
        test_pair = [pair_list[0][0][0].freq, pair_list[0][0][1].freq] # created the nested list
        self.assertEqual(test_pair, first_pair)

    def test_list_imd_calculation(self):
        imd = IntermodCalculator(start_freq=490, end_freq=600)
        freqs_to_test = [490, 491.5, 492.55, 493.325] 
        # IMD thirds - pair of freqs yields > IMD freqs
        # 490, 491.5 > 493
        # 490, 492.55 > 495.1
        # 490, 493.325 > 496.65
        # 491.5, 492.55 > 490.45, 493.6
        # 491.5, 493.325 > 495.150
        # 492.55, 493.325 > 491.775, 494.1
        # then calculate the IMDS against each other
        imd = IntermodCalculator(start_freq=490, end_freq=600)
        existing_freqs = [490, 491.5, 492.55, 493.325]
        freq_list1 = FrequencyList(existing_freqs)
        thirds, fifths = imd.calculate_imd_between_one_set_of_freqs(freq_list1)
        self.assertEqual(type(thirds), list)
        self.assertEqual(type(fifths), list)

    def test_freq_list_extend_methods(self):
        existing_freqs = [490, 491.5, 492.55, 493.325]
        f_list = FrequencyList(existing_freqs)
        f_list.append_(500)
        second_freq_list = [590, 591.5, 592.55, 593.325]    
        test_list = f_list.get_freq_values() + second_freq_list + [500]     
        f_list.extend(second_freq_list)
        for f in f_list.get_freq_values():
            self.assertIn(f, test_list)


if __name__ == '__main__':
    unittest.main()