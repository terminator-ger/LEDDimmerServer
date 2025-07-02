from LEDDimmerServer.utils import GlobalExceptionWatcher
import unittest
import sys
import os

class ColorConversionTest(unittest.TestCase):
    _table = [
        #["#FFFFFF",  	1	 ,   1	 ,   1		    ,None   ,0	    ,1    ],
        #["#808080",  	0.5	 ,   0.5 ,   0.5	   	,None   ,0	    ,0.5  ],
        #["#000000",  	0	 ,   0	 ,   0		    ,None   ,0	    ,0    ],
        ["#FF0000",  	1	 ,   0	 ,   0		    ,0.0    ,1	    ,0.333],
        ["#BFBF00",  	0.75 ,   0.75,	0		    ,60.0   ,1	    ,0.5  ],
        ["#008000",  	0	 ,   0.5 ,   0		    ,120.0 	,1	    ,0.167],
        ["#80FFFF",  	0.5	 ,   1	 ,   1		    ,180.0 	,0.4	,0.833],
        ["#8080FF",  	0.5	 ,   0.5 ,   1		    ,240.0 	,0.25	,0.667],
        ["#BF40BF",  	0.75 ,   0.25,	0.75		,300.0 	,0.571	,0.583],
        ["#A0A424",  	0.628,	0.643,	0.142		,61.5   ,0.699	,0.471],
        ["#411BEA",  	0.255,	0.104,	0.918		,250.0 	,0.756	,0.426],
        ["#1EAC41",  	0.116,	0.675,	0.255		,133.8 	,0.667	,0.349],
        ["#F0C80E",  	0.941,	0.785,	0.053		,50.5   ,0.911	,0.593],
        ["#B430E5",  	0.704,	0.187,	0.897		,284.8 	,0.686	,0.596],
        ["#ED7651",  	0.931,	0.463,	0.316		,13.2   ,0.446	,0.57 ],
        ["#FEF888",  	0.998,	0.974,	0.532		,57.4   ,0.363	,0.835],
        ["#19CB97",  	0.099,	0.795,	0.591		,163.4 	,0.8	,0.495],
        ["#362698",  	0.211,	0.149,	0.597		,247.3 	,0.533	,0.319],
        ["#7E7EB8",  	0.495,	0.493,	0.721		,240. 	,0.135	,0.57 ],
    ]
    @unittest.skip("Currently not used, but kept for reference")
    def test_rgb_to_hsi(self):
        with GlobalExceptionWatcher():
            from LEDDimmerServer.color import rgb_to_hsi, rgb2hsi
            for name, R, G, B, H, S, I in self._table:
                h, s, i = rgb2hsi(R, G, B)
                self.assertAlmostEqual(h, H, places=2)
                self.assertAlmostEqual(s, S, places=2)
                self.assertAlmostEqual(i, I, places=2)

    @unittest.skip("Currently not used, but kept for reference")
    def test_hsi_to_rgb(self):
        with GlobalExceptionWatcher():
            from LEDDimmerServer.color import hsi_to_rgb
            for name, R, G, B, H, S, I in self._table:
                r, g, b = hsi_to_rgb(H, S, I)
                self.assertAlmostEqual(r, R, places=2)
                self.assertAlmostEqual(g, G, places=2)
                self.assertAlmostEqual(b, B, places=2)
 