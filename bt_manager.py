import subprocess
import time
import logging

logger = logging.getLogger('OwrtMusicBox.Bluetooth')

class BluetoothManager:
    def run_command(self, command):
        try:
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, timeout=30)
            return result.decode('utf-8')
        except subprocess.CalledProcessError as e:
            logger.warning(f"BT command failed (non-fatal): {command[:50]}...")
            return e.output.decode('utf-8')
        except subprocess.TimeoutExpired:
            logger.error(f"BT command timed out: {command[:50]}...")
            return ""

    def parse_devices(self, raw_output):
        devices = []
        for line in raw_output.split('\n'):
            if "Device" in line:
                try:
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        devices.append({'mac': parts[1], 'name': parts[2].strip()})
                except: continue
        return devices

    def get_paired_devices(self):
        raw_output = self.run_command("bluetoothctl devices Paired")
        return self.parse_devices(raw_output)

    def scan_devices(self):
        logger.info("Starting Bluetooth scan...")
        paired = self.get_paired_devices()
        paired_macs = [d['mac'] for d in paired]
        all_devs_raw = self.run_command("bluetoothctl devices")
        all_devs = self.parse_devices(all_devs_raw)
        for dev in all_devs:
            if dev['mac'] not in paired_macs:
                self.run_command(f"bluetoothctl remove {dev['mac']}")
        try:
            scan_proc = subprocess.Popen(["bluetoothctl", "scan", "on"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)
            scan_proc.terminate()
            try: scan_proc.wait(timeout=1)
            except: scan_proc.kill()
        except Exception as e:
            logger.error(f"BT scan error: {e}")
        fresh_raw = self.run_command("bluetoothctl devices")
        fresh_list = self.parse_devices(fresh_raw)
        available_devices = []
        for dev in fresh_list:
            if dev['mac'] not in paired_macs:
                available_devices.append(dev)
        return available_devices

    def connect_device(self, mac_address):
        logger.info(f"Connecting to Bluetooth device: {mac_address}")
        self.run_command(f"bluetoothctl trust {mac_address}")
        self.run_command(f"bluetoothctl pair {mac_address}")
        result = self.run_command(f"bluetoothctl connect {mac_address}")
        if "Connection successful" in result:
            return True, "Berhasil terhubung!"
        elif "Failed to connect" in result:
            return False, "Gagal. Pastikan alat nyala & dekat."
        else:
            info = self.run_command(f"bluetoothctl info {mac_address}")
            if "Connected: yes" in info:
                return True, "Berhasil terhubung!"
            return False, "Gagal terhubung. Coba restart TWS/Speaker."

    def disconnect_device(self, mac_address):
        logger.info(f"Disconnecting Bluetooth device: {mac_address}")
        self.run_command(f"bluetoothctl disconnect {mac_address}")
        return True