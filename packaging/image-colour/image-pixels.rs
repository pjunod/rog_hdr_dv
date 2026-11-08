use gdk4::prelude::*;
use std::{convert::TryInto, env};
fn main() {
    glib::MainContext::default().block_on(async {
        for arg in env::args().skip(1) {
            let image = glycin::Loader::new(gio::File::for_path(&arg))
                .load()
                .await
                .unwrap();
            let frame = image.next_frame().await.unwrap();
            let tex = frame.texture();
            let mut read = gdk4::TextureDownloader::new(&tex);
            read.set_format(gdk4::MemoryFormat::R32g32b32a32Float);
            read.set_color_state(&gdk4::ColorState::rec2100_linear());
            let (bytes, stride) = read.download_bytes();
            assert!(stride >= tex.width() as usize * 16);
            print!(
                "{} {:?} {:?} {}x{}",
                std::path::Path::new(&arg)
                    .file_name()
                    .unwrap()
                    .to_string_lossy(),
                frame.color_state(),
                frame.memory_format(),
                tex.width(),
                tex.height()
            );
            for pixel in bytes.as_ref()[..tex.width() as usize * 16].chunks_exact(16) {
                let c: Vec<String> = pixel
                    .chunks_exact(4)
                    .map(|v| format!("{:.7}", f32::from_ne_bytes(v.try_into().unwrap())))
                    .collect();
                print!(" {}", c.join(","));
            }
            println!();
        }
    });
}
