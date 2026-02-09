use clap::Parser;

use AHControl::MotorController;
use std::{error::Error, thread, time::Duration};

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Serialport
    #[arg(short, long, default_value = "/dev/ttyACM0")]
    serialport: String,
    /// baudrate
    #[arg(short, long, default_value_t = 1_000_000)]
    baudrate: u32,
    /// id
    #[arg(short, long, default_value_t = 1)]
    id: u8,
    /// pos
    #[arg(short, long, default_value_t = 0.0)]
    pos: f64,
    /// Motor model (SCS0009 or STS3032)
    #[arg(short, long, default_value = "SCS0009")]
    model: String,
}

fn main() -> Result<(), Box<dyn Error>> {
    let args = Args::parse();
    let serialport: String = args.serialport;
    let baudrate: u32 = args.baudrate;
    let id: u8 = args.id;
    let pos: f64 = args.pos;
    let model: String = args.model;

    println!("Opening port {serialport} at baudrate {baudrate}");
    println!("Moving motor ({id}) to the pos: {pos}");

    let serial_port = serialport::new(serialport, baudrate)
        .timeout(Duration::from_millis(10))
        .open()?;

    let mut controller = MotorController::new(&model, serial_port)?;

    let curpos = controller.read_present_position(id)?;
    println!("Current pos: {:?}", curpos);
    controller.write_torque_enable(id, 1)?;
    thread::sleep(Duration::from_millis(1000));
    controller.write_goal_position(id, pos)?;
    thread::sleep(Duration::from_millis(1000));
    println!("Quitting");
    Ok(())
}
