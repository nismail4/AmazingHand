use std::error::Error;

use rustypot::servo::feetech::{scs0009::Scs0009Controller, sts3032::Sts3032Controller};

pub enum MotorController {
    Scs0009(Scs0009Controller),
    Sts3032(Sts3032Controller),
}

impl MotorController {
    pub fn new(model: &str, serial_port: Box<dyn serialport::SerialPort>) -> Result<Self, String> {
        match model {
            "SCS0009" => Ok(MotorController::Scs0009(
                Scs0009Controller::new()
                    .with_protocol_v1()
                    .with_serial_port(serial_port),
            )),
            "STS3032" => Ok(MotorController::Sts3032(
                Sts3032Controller::new()
                    .with_protocol_v1()
                    .with_serial_port(serial_port),
            )),
            _ => Err(format!("Unsupported motor model: {model}")),
        }
    }

    pub fn sync_write_torque_enable(
        &mut self,
        ids: &[u8],
        values: &[u8],
    ) -> Result<(), Box<dyn Error>> {
        match self {
            MotorController::Scs0009(c) => c.sync_write_torque_enable(ids, values),
            MotorController::Sts3032(c) => c.sync_write_raw_torque_enable(ids, values),
        }
    }

    pub fn write_torque_enable(&mut self, id: u8, value: u8) -> Result<(), Box<dyn Error>> {
        match self {
            MotorController::Scs0009(c) => c.write_torque_enable(id, value),
            MotorController::Sts3032(c) => c.write_raw_torque_enable(id, value),
        }
    }

    pub fn sync_write_goal_position(
        &mut self,
        ids: &[u8],
        values: &[f64],
    ) -> Result<(), Box<dyn Error>> {
        match self {
            MotorController::Scs0009(c) => c.sync_write_goal_position(ids, values),
            MotorController::Sts3032(c) => c.sync_write_goal_position(ids, values),
        }
    }

    pub fn write_goal_position(&mut self, id: u8, value: f64) -> Result<(), Box<dyn Error>> {
        match self {
            MotorController::Scs0009(c) => c.write_goal_position(id, value),
            MotorController::Sts3032(c) => c.write_goal_position(id, value),
        }
    }

    pub fn read_present_position(&mut self, id: u8) -> Result<Vec<f64>, Box<dyn Error>> {
        match self {
            MotorController::Scs0009(c) => c.read_present_position(id),
            MotorController::Sts3032(c) => c.read_present_position(id),
        }
    }

    pub fn write_id(&mut self, old_id: u8, new_id: u8) -> Result<(), Box<dyn Error>> {
        match self {
            MotorController::Scs0009(c) => c.write_id(old_id, new_id),
            MotorController::Sts3032(c) => c.write_id(old_id, new_id),
        }
    }

    pub fn read_id(&mut self, id: u8) -> Result<Vec<u8>, Box<dyn Error>> {
        match self {
            MotorController::Scs0009(c) => c.read_id(id),
            MotorController::Sts3032(c) => c.read_id(id),
        }
    }
}
