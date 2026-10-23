import unittest
from railway import parse_route,segment_view

XML=b'''<osm version="0.6">
  <node id="1" lat="29.0000" lon="-95"><tag k="railway" v="tram_stop"/><tag k="name" v="Alpha"/></node>
  <node id="2" lat="29.0005" lon="-95"><tag k="railway" v="switch"/></node>
  <node id="3" lat="29.001" lon="-95"><tag k="railway" v="tram_stop"/><tag k="name" v="Bravo"/></node>
  <node id="4" lat="29.0005" lon="-95.01"><tag k="railway" v="switch"/></node>
  <way id="22"><nd ref="1"/><nd ref="2"/><nd ref="3"/><tag k="railway" v="light_rail"/></way>
  <way id="23"><nd ref="3"/><nd ref="4"/><tag k="railway" v="light_rail"/></way>
  <relation id="123"><member type="way" ref="22" role=""/><member type="node" ref="1" role="stop"/><member type="node" ref="3" role="stop"/><tag k="name" v="Test Line"/></relation>
</osm>'''
class TestRoute(unittest.TestCase):
    def test_extraction_only_direct_relation_ways(self):
        result=parse_route(XML,123)
        self.assertEqual([x['id'] for x in result['switches']],['2'])
        self.assertEqual(len(result['stations']),2)
    def test_segment(self):
        route=parse_route(XML,123)
        s=segment_view(route,'node:1','node:3')
        self.assertEqual([x['id'] for x in s['switches']],['2'])
        self.assertGreater(s['distance_m'],0)
    def test_unknown_station(self):
        with self.assertRaises(ValueError):
            segment_view(parse_route(XML,123),'node:1','node:999')
if __name__=='__main__':unittest.main()
