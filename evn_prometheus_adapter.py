#!/usr/bin/env python3

from xml.etree import ElementTree

class ElementTreeToPrometheusAdapter:
    OCTET_STRING_CODES = {
        '0100010800FF': {
            'name': 'mbus_import_energy_active',
            'help': 'Wirkenergie A+',
            'type': 'counter',
        },
        '0100020800FF': {
            'name': 'mbus_export_energy_active',
            'help': 'Wirkenergie A-',
            'type': 'counter',
        },
        '0100010700FF': {
            'name': 'mbus_total_power_active',
            'help': 'Momentanleistung P+',
            'type': 'gauge',
        },
        '0100020700FF': {
            'name': 'mbus_total_export_power_demand_active',
            'help': 'Momentanleistung P-',
            'type': 'gauge',
        },
        '0100200700FF': {
            'name': 'mbus_l1_voltage',
            'help': 'Spannung L1',
            'type': 'gauge',
        },
        '0100340700FF': {
            'name': 'mbus_l2_voltage',
            'help': 'Spannung L2',
            'type': 'gauge',
        },
        '0100480700FF': {
            'name': 'mbus_l3_voltage',
            'help': 'Spannung L3',
            'type': 'gauge',
        },
        '01001F0700FF': {
            'name': 'mbus_l1_current',
            'help': 'Strom L1',
            'type': 'gauge',
        },
        '0100330700FF': {
            'name': 'mbus_l2_current',
            'help': 'Strom L2',
            'type': 'gauge',
        },
        '0100470700FF': {
            'name': 'mbus_l3_current',
            'help': 'Strom L3',
            'type': 'gauge',
        },
        '01000D0700FF': {
            'name': 'mbus_total_power_factor',
            'help': 'Leistungsfaktor',
            'type': 'gauge',
        },
    }
    UNIT_CODES = {
        '1E': 'Wh',
        '1B': 'W',
        '23': 'V',
        '21': 'A',
        'FF': '1',
    }

    def __init__(self, instrument, instrument_human_name, instrument_type, xml):
        self.instrument = instrument
        self.instrument_human_name = instrument_human_name
        self.instrument_type = instrument_type
        self.root = ElementTree.fromstring(xml)
        *_, last = self.root.iter()
        self.counter_number = last.attrib['Value']
            

    def prometheus_format(self):
        iterator = self.root.iter()
        lines = []
        for item in iterator:
            if item.tag == 'OctetString' and 'Value' in item.attrib:
                key = item.attrib['Value']
                if key in self.OCTET_STRING_CODES.keys():
                    name = self.OCTET_STRING_CODES[key]['name']
                    value = next(iterator).attrib['Value']
                    next(iterator)
                    scale_factor = self.__scale_factor(next(iterator).attrib['Value'])
                    value = scale_factor * int.from_bytes(bytearray.fromhex(value), byteorder='big', signed=True)
                    unit = self.UNIT_CODES[next(iterator).attrib['Value']]
                    if 'help' in self.OCTET_STRING_CODES[key]:
                        hlp = self.OCTET_STRING_CODES[key]['help']
                        lines.append(f"# HELP {name} {hlp}")
                    if 'type' in self.OCTET_STRING_CODES[key]:
                        tp = self.OCTET_STRING_CODES[key]['type']
                        lines.append(f"# TYPE {name} {tp}")
                    lines.append(f"{name}{'{'}instrument=\"{self.instrument}\",instrument_human_name=\"{self.instrument_human_name}\",instrument_type=\"{self.instrument_type}\",unit=\"{unit}\"{'}'} {value}")
        content = "\n".join(lines)
        return f"{content}\n"

    def __scale_factor(self, value):
        exponent = int.from_bytes(
            bytearray.fromhex(value),
            byteorder='big',
            signed=True
        )
        return 10.0 ** exponent
