# -*- coding: gbk -*-
import serial
import time
from log_manager import LogManager
from serial import SerialException


class LightController:
    """灯光控制器"""
    
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.is_light_on = False
    
    def _init_serial(self):
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
            parity=serial.PARITY_NONE,
            timeout=1
        )

    def turn_on(self):
        try:
            self._init_serial()
            # 红灯亮指令
            hex_data = [0xFF, 0x04, 0x01, 0x03,0xAA]
            self.ser.write(bytes(hex_data))
            self.is_light_on = True
            self.close()
            LogManager.append_log("红灯已打开", "INFO")
            return True
        except SerialException as e:
            print(f"串口操作失败：{e}")
            return False
        except Exception as e:
            print(f"其他错误：{e}")
            return False

    def turn_off(self):
        try:
            self._init_serial()
            # 关灯指令
            hex_data = [0xFF, 0x01, 0x01, 0x03,0xAA]
            self.ser.write(bytes(hex_data))
            self.is_light_on = False
            self.close()
            LogManager.append_log("红灯已关闭", "INFO")
            return True
        except Exception as e:
            LogManager.append_log(f"关灯失败: {str(e)}", "ERROR")
            return False

    def close(self):
        self.ser.close()
   