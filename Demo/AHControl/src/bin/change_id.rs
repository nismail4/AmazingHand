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
    /// old id
    #[arg(short, long, default_value_t = 1)]
    old_id: u8,
    /// new id
    #[arg(short, long)]
    new_id: u8,
    /// Motor model (SCS0009 or STS3032)
    #[arg(short, long, default_value = "SCS0009")]
    model: String,
}

fn main() -> Result<(), Box<dyn Error>> {
    let args = Args::parse();
    let serialport: String = args.serialport;
    let baudrate: u32 = args.baudrate;
    let old_id: u8 = args.old_id;
    let new_id: u8 = args.new_id;
    let model: String = args.model;

    println!("Opening port {serialport} at baudrate {baudrate}");
    println!("Changing id: {old_id} into {new_id}");

    let serial_port = serialport::new(serialport, baudrate)
        .timeout(Duration::from_millis(10))
        .open()?;

    let mut controller = MotorController::new(&model, serial_port)?;

    controller.write_id(old_id, new_id)?;
    thread::sleep(Duration::from_millis(1000));
    controller.read_id(new_id)?;
    println!("Quitting");
    Ok(())
}
