#/usr/bin/python

import time

import Adafruit_I2C

class L3GD20_I2C:
  base_device_address = 0x6a
  who_am_i_expected_value = 0xd4

  WHO_AM_I = 0x0f

  CTRL_REG1 = 0x20
  EN_XYZ_FLAGS = 0b00001111

  CTRL_REG4 = 0x23
  CONT_UPDATE_FLAGS = 0b00110000

  CTRL_REG5 = 0x24
  FIFO_EN_FLAG = 64
  REBOOT_MEMORY_CONTENT_FLAG = 128

  OUT_TEMP = 0x26

  STATUS_REG = 0x27
  XYZ_AVAILABLE_MASK = 8

  OUT_X_L = 0x28
  OUT_X_H = 0x29
  OUT_Y_L = 0x2a
  OUT_Y_H = 0x2b
  OUT_Z_L = 0x2c
  OUT_Z_H = 0x2d

  def __init__(self, devnum=0):
    if (devnum not in (0, 1)):
      raise ValueError("devnum must be 0 or 1")
    self.addr = L3GD20_I2C.base_device_address + devnum
    self.i2c_dev = Adafruit_I2C.Adafruit_I2C(self.addr)
    self.reboot_memory_content()

    if not self.check_who_am_i():
      raise RuntimeError("there does not seem to ba an L3GD20 attached at address " + str(self.addr))

    self.enable_xyz()
    self.enable_continuous_update()

    self.set_sensitivity(250)

    self.detect_drift()
    self.zero()

  def zero(self):
    self.orientation = (0.0, 0.0, 0.0)
    self.last_reading = time.time()

  def detect_drift(self):
    print "detecting gyro drift (do not move!)"
    self.drift = (0.0, 0.0, 0.0)
    self.zero()
    start_time = time.time()
    for i in xrange(1000):
      self.poll()
    end_orientation = self.poll()
    end_time = time.time()
    dtime = end_time - start_time
    drift = tuple([x / dtime for x in end_orientation])
    self.drift = drift
    self.zero()
    print "done detecting gyro drift"

  def poll(self):
    movement = self.get_xyz_deg()
    new_time = time.time()
    dtime = new_time - self.last_reading
    self.last_reading = new_time
    delta = tuple([x * dtime - drift * dtime for x, drift in zip(movement, self.drift)])

    self.orientation = tuple([x + d for x, d in zip(self.orientation, delta)])
    return self.orientation

  def reboot_memory_content(self):
    orig_value = self.i2c_dev.readU8(L3GD20_I2C.CTRL_REG5)
    self.i2c_dev.write8(L3GD20_I2C.CTRL_REG5, L3GD20_I2C.REBOOT_MEMORY_CONTENT_FLAG)
    # sleep 2 seconds to make sure it worked...
    time.sleep(2)

  def enable_fifo(self):
    orig_value = self.i2c_dev.readU8(L3GD20_I2C.CTRL_REG5)
    self.i2c_dev.write8(L3GD20_I2C.CTRL_REG5, orig_value | L3GD20_I2C.FIFO_EN_FLAG)

  def enable_xyz(self):
    self.i2c_dev.write8(L3GD20_I2C.CTRL_REG1, L3GD20_I2C.EN_XYZ_FLAGS)

  def enable_continuous_update(self):
    self.i2c_dev.write8(L3GD20_I2C.CTRL_REG4, L3GD20_I2C.CONT_UPDATE_FLAGS)

  # check WHO_AM_I_REGISTER
  # returns True if it matches the expected
  # value and false otherwise
  def check_who_am_i(self):
    return self.i2c_dev.readU8(L3GD20_I2C.WHO_AM_I) == L3GD20_I2C.who_am_i_expected_value

  def check_xyz_available(self):
    return (self.i2c_dev.readU8(L3GD20_I2C.STATUS_REG) & L3GD20_I2C.XYZ_AVAILABLE_MASK) != 0

  def get_temp(self):
    return self.i2c_dev.readS8(L3GD20_I2C.OUT_TEMP)

  def get_x(self):
    return self.i2c_dev.readS16Rev(L3GD20_I2C.OUT_X_L)

  def get_y(self):
    return self.i2c_dev.readS16Rev(L3GD20_I2C.OUT_Y_L)

  def get_z(self):
    return self.i2c_dev.readS16Rev(L3GD20_I2C.OUT_Z_L)

  def get_xyz(self):
    while not self.check_xyz_available():
      pass
    return (self.get_x(), self.get_y(), self.get_z())

  def get_xyz_deg(self):
    return tuple([self.gain * x for x in self.get_xyz()])

  def set_sensitivity(self, dps):
    if dps not in (250, 500, 2000):
      raise ValueError("invalid dps (must be in 250, 500, 2000)")
    if dps == 250:
      flag = 0b00 << 1
      self.gain = 0.00875
    elif dps == 500:
      flag = 0b01 << 1
      self.gain = 0.0175
    else:
      flag = 0b10 << 1
      self.gain = 0.07

    orig_value = self.i2c_dev.readU8(L3GD20_I2C.CTRL_REG4)
    self.i2c_dev.write8(L3GD20_I2C.CTRL_REG4, orig_value | flag)

if __name__ == "__main__":
  # if this is the main executable, just do a quick test
  gyro = L3GD20_I2C()
  print "device temperature: " + str(gyro.get_temp())
  print "L3GD20_I2C tests completed"
  while True:
    print "orientation values: " + str(gyro.poll())