// SPDX-License-Identifier: MIT
// Test-only mutation of a genuine seed RPU. dolby_vision 3.3.2 writes valid CRC.
use dolby_vision::rpu::dovi_rpu::DoviRpu;
use std::{env, fs};
fn main() {
    let args: Vec<_> = env::args().collect();
    let seed = fs::read(&args[1]).unwrap();
    let parsed = DoviRpu::parse_unspec62_nalu(&seed).unwrap();
    assert!(!parsed.header.use_prev_vdr_rpu_flag);
    assert_eq!(parsed.rpu_data_mapping.as_ref().unwrap().vdr_rpu_id, 0);
    for (id, name) in [(7, "missing7.nal"), (0, "reuse0.nal")] {
        let mut rpu = parsed.clone();
        rpu.header.use_prev_vdr_rpu_flag = true;
        rpu.header.prev_vdr_rpu_id = id;
        rpu.rpu_data_mapping = None;
        rpu.modified = true;
        let bytes = rpu.write_hevc_unspec62_nalu().unwrap();
        // Independent parse validates syntax and the regenerated CRC.
        let check = DoviRpu::parse_unspec62_nalu(&bytes).unwrap();
        assert_eq!(check.header.prev_vdr_rpu_id, id);
        fs::write(format!("{}/{}", args[2], name), bytes).unwrap();
    }
}
