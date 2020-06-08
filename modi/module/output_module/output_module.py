import json
import struct
import base64
import time

from enum import IntEnum
from typing import Tuple, List
from modi.module.module import Module


class OutputModule(Module):
    def __init__(self, id_, uuid, msg_send_q):
        super().__init__(id_, uuid, msg_send_q)

    class PropertyDataType(IntEnum):
        INT = 0
        FLOAT = 1
        STRING = 2
        RAW = 3
        DISPLAY_VAR = 4

    def _update_properties(self, property_types: List[IntEnum],
                           values: Tuple) -> None:
        """Update the properties when setting the property

        :param property_types: PropertyType class of the module
        :param values: values in correct order
        :return: None
        """
        for property_type, property_value in zip(property_types, values):
            if property_type not in self._properties:
                self._properties[property_type] = self.Property()
                request_property_msg = self.request_property(
                    self._id, property_type
                )
                self._msg_send_q.put(request_property_msg)
                self._properties[property_type].last_request_time = time.time()

            self.update_property(property_type, property_value)

    def __parse_data(self, property_data_type: IntEnum,
                     property_values: Tuple):
        if property_data_type is None:
            property_data_type = self.PropertyDataType.INT

        property_values_bytes = bytearray(8)

        if property_data_type == self.PropertyDataType.INT:
            for index, property_value in enumerate(property_values):
                property_value = int(property_value)
                property_values_bytes[index * 2] = property_value & 0xFF
                property_values_bytes[index * 2 + 1] = (
                    (property_value & 0xFF00) >> 8
                )
        elif property_data_type == self.PropertyDataType.FLOAT:
            for index, property_value in enumerate(property_values):
                property_values_bytes[index * 4: index * 4 + 4] = struct.pack(
                    "f", float(property_value)
                )
        elif property_data_type == self.PropertyDataType.STRING:
            pass

    def _set_property(self, destination_id: int,
                      property_type: IntEnum, property_values: Tuple,
                      property_data_type: IntEnum = None) -> str:
        """ Generate message for setting property
        """
        message = dict()

        message["c"] = 0x04
        message["s"] = property_type
        message["d"] = destination_id
        # Generate property according to their property type
        property_values_bytes = bytearray(8)
        if (
            property_data_type is None
            or property_data_type == self.PropertyDataType.INT
        ):
            for index, property_value in enumerate(property_values):
                property_value = int(property_value)
                property_values_bytes[index * 2] = property_value & 0xFF
                property_values_bytes[index * 2 +
                                      1] = (property_value & 0xFF00) >> 8
        elif property_data_type == self.PropertyDataType.FLOAT:
            for index, property_value in enumerate(property_values):
                property_values_bytes[index * 4: index * 4 + 4] = struct.pack(
                    "f", float(property_value)
                )

        elif property_data_type == self.PropertyDataType.STRING:
            messages = list()
            property_value = str(property_values)[:27]
            number_of_chunks = int(len(property_value) / 8) + 1

            for index in range(number_of_chunks):
                property_values_bytes[:] = [
                    ord(character)
                    for character in property_value[index * 8: index * 8 + 8]
                ]
                message["b"] = base64.b64encode(
                    bytes(property_values_bytes)
                ).decode("utf-8")
                message["l"] = len(property_values_bytes)
                messages.append(json.dumps(message, separators=(",", ":")))
            return messages

        elif property_data_type == self.PropertyDataType.RAW:
            message["b"] = base64.b64encode(
                bytearray(property_values)).decode("utf-8")
            message["l"] = len(property_values)

        elif property_data_type == self.PropertyDataType.DISPLAY_VAR:
            property_values_bytes[:4] = struct.pack(
                "f", float(property_values[0]))
            property_values_bytes[4] = property_values[1]
            property_values_bytes[5] = 0x00
            property_values_bytes[6] = property_values[2]
            property_values_bytes[7] = 0x00
        else:
            raise RuntimeError("Not supported property data type.")
        message["b"] = base64.b64encode(
            bytes(property_values_bytes)).decode("utf-8")
        message["l"] = 8

        return json.dumps(message, separators=(",", ":"))
