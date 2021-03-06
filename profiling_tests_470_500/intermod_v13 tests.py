# intermod_v10 tests
import unittest
from intermod_v13 import IntermodCalculator, Coordination, FrequencyList, EquipmentModel

"""
lots of refactoring happened in V10, so build new tests for it
"""

class TestIMDCalculator(unittest.TestCase):
    
    def test_two_transmitter_calculations(self):
        imd = IntermodCalculator(start_freq=490,end_freq=600)
        f1 = 525
        f2 = 525.125
        third_order, fifth_order, triples = imd.calculate_two_transmitter_imds(f1, f2)
        result_thirds = set([524.875, 525.25])
        self.assertEqual(third_order, result_thirds)
        for freq in third_order:
            self.assertGreaterEqual(freq, imd.start_freq)
            self.assertLessEqual(freq, imd.end_freq)

    def test_three_transmitter_calculations(self):
        imd = IntermodCalculator(start_freq=490,end_freq=600)
        f1 = 500
        f2 = 501
        f3 = 505
        third_order, fifth_order, triples = imd.calculate_three_transmitter_imds(f1,f2,f3)
        third_results = set([499,502,495,510,497,509])
        fifth_results = set([513,493,515,490,503, 498])
        triples_results = set([496,504,506])
        self.assertEqual(fifth_order, fifth_results)
        self.assertEqual(third_order, third_results)
        self.assertEqual(triples, triples_results)


    def test_freq_list_pair_creation(self):

        existing_freqs = [1,2,3,4]
        freq_list1 = FrequencyList(existing_freqs) # we didn't supply an added freq, so it should be
        expected_result = [(1,2),(1,3),(1,4),(2,3),(2,4),(3,4)]
        result = list(freq_list1.create_freq_test_list_from_itself())
        self.assertEqual(expected_result, result)
        

    def test_freq_list_extend_methods(self):
        existing_freqs = [490, 491.5, 492.55, 493.325]
        f_list = FrequencyList(existing_freqs)
        f_list.append_(500)
        second_freq_list = [590, 591.5, 592.55, 593.325]    
        test_list = f_list.get_freq_values() + second_freq_list + [500]     
        f_list.extend(second_freq_list)
        for f in f_list.get_freq_values():
            self.assertIn(f, test_list)

    def test_coord_default_instance(self):
        coord = Coordination()
        self.assertEqual(coord.default_bandwidth, 0.299)

    def test_coord_test_one_freq(self):
        coord = Coordination()
        imd_thirds = [470,480,490]
        imd_fifths = [500,510,520]
        coord.imd_thirds = imd_thirds
        coord.imd_fifths = imd_fifths
        failing_test_freqs_for_in_imd_products = [470, 500]
        passing_test_freqs = []
        for freq in failing_test_freqs_for_in_imd_products:
            result = coord.test_one_freq(freq)
            self.assertEqual(False, result)
        # add a freq to the coordination to check for spacing test
        coord.coordinated_freqs.append_(481)
        result = coord.test_one_freq(481)
        self.assertEqual(False,result)
        
        return

    def test_ias_known_good_freqs(self):
        """
        this list of freqs is "coordinated" based on what IAS tells us.  
        """
        # this file just has thirds calculated by IAS
        with open('ias_accepted_3rdfreqs.txt', 'r') as inFile:
            fList = []
            for f in inFile.readline().split(','):
                fList.append(float(f))
            coord = Coordination(triples=False)
            list_of_freqs = FrequencyList(fList).create_freq_test_list_from_itself()
            thirds, fifths,triples = coord.imd_calc.calculate_imd_between_one_set_of_freqs(list_of_freqs)
            bad_freqs = []
            for f in fList:
                if f in thirds:
                    bad_freqs.append(f)
            #print('there are {0} freqs from the original list in the imd calculation!'.format(len(bad_freqs)))
            # if my calculations are right, then len(bad_freqs) should be zero
            self.assertEqual(len(bad_freqs), 0)
        # this file has thirds and fifths calculated by IAS
        with open('ias_accepted_3rdAnd5thfreqs.txt', 'r') as inFile:
            fList = []
            for f in inFile.readline().split(','):
                fList.append(float(f))
            coord = Coordination(triples=False)
            list_of_freqs = FrequencyList(fList).create_freq_test_list_from_itself()
            thirds, fifths,triples = coord.imd_calc.calculate_imd_between_one_set_of_freqs(list_of_freqs)
            bad_freqs = []
            for f in fList:
                if f in thirds or f in fifths:
                    bad_freqs.append(f)
            self.assertEqual(len(bad_freqs), 0)
            #print('there are {0} freqs from the original list in the imd calculation!'.format(len(bad_freqs)))

    def test_freqs_to_avoid(self):
        """
        freqs to avoid only 
        """
        coord = Coordination(triples=False)
        coord.freqs_to_avoid = [470, 471, 472, 473, 474, 475, 476]
        coord.calculate(start_freq=470, end_freq=500)
        for f in coord.freqs_to_avoid:
            self.assertNotIn(f, coord.coordinated_freqs.get_freq_values())
            self.assertNotIn(f, coord.uncoordinated_freqs.get_freq_values())

    def test_a_model(self):
        model = EquipmentModel(start_freq=501, end_freq=600, bandwidth=0.500, imd_triple_beats=False)
        coord = Coordination(triples=True) # model should override this behavior?
        coord.accept_equipment_model(model)
        self.assertEqual(coord.start_freq, model.start_freq)
        self.assertEqual(coord.end_freq, model.end_freq)
        self.assertEqual(coord.triple_beats, False)

    def test_a_model_coordination(self):
        model = EquipmentModel(start_freq=501, end_freq=504, bandwidth=0.500, imd_triple_beats=False)
        coord = Coordination(triples=True)
        coord.calculate(equipment_model=model)
        freqs = coord.coordinated_freqs.get_freq_values()
        for f in freqs:
            self.assertGreater(f, coord.start_freq)
            self.assertLessEqual(f, coord.end_freq)


    def test_given_explicit_freqs(self):
        """
        give an explicit list to pick freqs from. This will be usd with Models
        """
        model = EquipmentModel(start_freq=470, end_freq=480, bandwidth=0.500, imd_triple_beats=False)
        coord = Coordination(triples=True)
        frequencies = []
        for x in range(470,480):
            frequencies.append(x)
        coord.calculate(equipment_model=model, test_freqs=frequencies)
        coordinated_freqs = coord.coordinated_freqs.get_freq_values()
        frequencies = []
        for x in range(470,480):
            frequencies.append(x)
        for x in coordinated_freqs:
            self.assertIn(x, frequencies)





        



if __name__ == '__main__':
    unittest.main()
