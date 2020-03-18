from unittest import TestCase


class Testcalc_astral_day_time(TestCase):
    def test_calc_astral_day_time(self):
        from utils import calc_astral_day_time
        from datetime import date, time
        Date = date(2015, 1, 1)
        Latitude = 15
        print("Test calc_astral_day_time")
        # Test Longitude 0° 'dawn/aube':15h35 ,'sunrise/levé': 6h25  , 'sunset/coucher': 17h41, 'dusk/crepuscule':18h31
        self.assertEqual(calc_astral_day_time(Date, time(12,0,0), Latitude, 0 ),'D') # 12h Day
        self.assertEqual(calc_astral_day_time(Date, time(23,0,0), Latitude, 0 ),'N') # 12h Night
        self.assertEqual(calc_astral_day_time(Date, time( 1,0,0), Latitude, 0 ),'N') #  1h Night
        self.assertEqual(calc_astral_day_time(Date, time( 6,0,0), Latitude, 0 ),'A') #  6h Dawn
        self.assertEqual(calc_astral_day_time(Date, time(18,0,0), Latitude, 0 ),'U') # 18h Dusk
        # 'dawn/aube':17h36 ,'sunrise/levé': 18h26  , 'sunset/coucher': 5h41, 'dusk/crepuscule':6h31
        self.assertEqual(calc_astral_day_time(Date, time(12, 0, 0), Latitude, -180), 'N')  # 12h 180 Nigth
        self.assertEqual(calc_astral_day_time(Date, time(18, 0, 0), Latitude, -180), 'A')  # 18h 180 Dawn
        self.assertEqual(calc_astral_day_time(Date, time(19, 0, 0), Latitude, -180), 'D')  # 19h 180 Day
        self.assertEqual(calc_astral_day_time(Date, time( 2, 0, 0), Latitude, -180), 'D')  #  2h 180 Day
        self.assertEqual(calc_astral_day_time(Date, time( 6, 0, 0), Latitude, -180), 'U')  #  6h 180 dusk
        self.assertEqual(calc_astral_day_time(Date, time( 7, 0, 0), Latitude, -180), 'N')  #  7h 180 Nigth
