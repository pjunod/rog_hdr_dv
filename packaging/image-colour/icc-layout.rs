// SPDX-License-Identifier: MIT
// Compile against Loupe's existing dependency artifacts. This includes the
// actual candidate ICC implementation, without changing the product crate.
use glycin::{ColorState, Error};
use glycin_common::MemoryFormat;
use glycin_utils::{BinaryData, Frame};
mod dbus {
    pub const MAX_TEXTURE_SIZE: u64 = 8 * 10u64.pow(9);
}
mod icc {
    include!(concat!(
        env!("LOUPE_SOURCE"),
        "/debian/missing-sources/glycin/src/icc.rs"
    ));
}

fn run(
    format: MemoryFormat,
    input: &[u8],
    width: u32,
    stride: u32,
    height: u32,
    profile: &[u8],
) -> (Frame, Vec<u8>) {
    let mut frame = Frame {
        width,
        height,
        stride,
        memory_format: format,
        texture: BinaryData::from_data(input).unwrap(),
        delay: None.into(),
        details: Default::default(),
    };
    eprintln!("ICC layout: {format:?}");
    let (pixels, state) = icc::apply_transformation(profile, &mut frame, input).unwrap();
    assert!(matches!(state, ColorState::Cicp(c) if c == gufo_common::cicp::Cicp::REC2020_LINEAR));
    (frame, pixels.into_vec())
}
fn half_pixels(bytes: &[u8]) -> Vec<f32> {
    bytes
        .chunks_exact(2)
        .map(|p| half::f16::from_bits(u16::from_ne_bytes(p.try_into().unwrap())).to_f32())
        .collect()
}
fn floats(bytes: &[u8]) -> Vec<f32> {
    bytes
        .chunks_exact(4)
        .map(|p| f32::from_ne_bytes(p.try_into().unwrap()))
        .collect()
}
fn main() {
    let srgb = lcms2::Profile::new_srgb().icc().unwrap();
    let mut straight = Vec::new();
    let mut associated = Vec::new();
    for (rgb, a) in [
        [255u8, 0, 0],
        [0, 255, 0],
        [0, 0, 255],
        [255; 3],
        [48, 128, 200],
    ]
    .into_iter()
    .zip([1u8, 32, 128, 254, 255])
    {
        straight.extend_from_slice(&rgb);
        straight.push(a);
        for c in rgb {
            associated.push((u16::from(c) * u16::from(a) / 255) as u8);
        }
        associated.push(a);
    }
    let (_, expected) = run(MemoryFormat::R8g8b8a8, &straight, 5, 20, 1, &srgb);
    let (_, actual) = run(
        MemoryFormat::R8g8b8a8Premultiplied,
        &associated,
        5,
        20,
        1,
        &srgb,
    );
    assert_eq!(
        expected, actual,
        "8-bit associated RGB must unassociate before ICC conversion"
    );
    for (format, order) in [
        (MemoryFormat::B8g8r8a8Premultiplied, [2usize, 1, 0, 3]),
        (MemoryFormat::A8r8g8b8Premultiplied, [3usize, 0, 1, 2]),
    ] {
        let mut encoded = Vec::new();
        for pixel in associated.chunks_exact(4) {
            for i in order {
                encoded.push(pixel[i]);
            }
        }
        let (_, actual) = run(format, &encoded, 5, 20, 1, &srgb);
        assert_eq!(expected, actual, "channel order must survive unassociation");
    }
    let gray = lcms2::Profile::new_gray(&lcms2::CIExyY::d50(), &lcms2::ToneCurve::new(2.2))
        .unwrap()
        .icc()
        .unwrap();
    let (_, gray8) = run(MemoryFormat::G8a8, &[255, 128], 1, 2, 1, &gray);
    let (_, gray8_associated) = run(MemoryFormat::G8a8Premultiplied, &[128, 128], 1, 2, 1, &gray);
    assert_eq!(gray8, gray8_associated);
    let gray16_straight: Vec<u8> = [65535u16, 32768]
        .into_iter()
        .flat_map(u16::to_ne_bytes)
        .collect();
    let gray16_premul: Vec<u8> = [32768u16, 32768]
        .into_iter()
        .flat_map(u16::to_ne_bytes)
        .collect();
    let (_, gray16) = run(MemoryFormat::G16a16, &gray16_straight, 1, 4, 1, &gray);
    let (_, gray16_associated) = run(
        MemoryFormat::G16a16Premultiplied,
        &gray16_premul,
        1,
        4,
        1,
        &gray,
    );
    assert_eq!(gray16, gray16_associated);
    let (_, transparent) = run(
        MemoryFormat::R8g8b8a8Premultiplied,
        &[0, 0, 0, 0],
        1,
        4,
        1,
        &srgb,
    );
    assert!(half_pixels(&transparent).iter().all(|v| *v == 0.));
    let mut padded = straight.clone();
    padded.extend_from_slice(&[0x5a; 3]);
    padded.extend_from_slice(&straight);
    padded.extend_from_slice(&[0xa5; 3]);
    let (frame, actual) = run(MemoryFormat::R8g8b8a8, &padded, 5, 23, 2, &srgb);
    assert_eq!(frame.stride, 40);
    assert_eq!(
        actual,
        expected.repeat(2),
        "row padding must never enter the ICC transform"
    );
    let straight16: Vec<u8> = [65535u16, 0, 0, 32768]
        .into_iter()
        .flat_map(u16::to_ne_bytes)
        .collect();
    let associated16: Vec<u8> = [32768u16, 0, 0, 32768]
        .into_iter()
        .flat_map(u16::to_ne_bytes)
        .collect();
    let (frame, expected16) = run(MemoryFormat::R16g16b16a16, &straight16, 1, 8, 1, &srgb);
    let (_, actual16) = run(
        MemoryFormat::R16g16b16a16Premultiplied,
        &associated16,
        1,
        8,
        1,
        &srgb,
    );
    assert_eq!(frame.memory_format, MemoryFormat::R32g32b32a32Float);
    assert_eq!(expected16, actual16);
    let straight32: Vec<u8> = [1f32, 0., 0., 0.5]
        .into_iter()
        .flat_map(f32::to_ne_bytes)
        .collect();
    let associated32: Vec<u8> = [0.5f32, 0., 0., 0.5]
        .into_iter()
        .flat_map(f32::to_ne_bytes)
        .collect();
    let (_, expected32) = run(
        MemoryFormat::R32g32b32a32Float,
        &straight32,
        1,
        16,
        1,
        &srgb,
    );
    let (_, actual32) = run(
        MemoryFormat::R32g32b32a32FloatPremultiplied,
        &associated32,
        1,
        16,
        1,
        &srgb,
    );
    assert_eq!(expected32, actual32);
    // Invalid profiles must leave the original layout untouched.
    let mut frame = Frame {
        width: 1,
        height: 1,
        stride: 4,
        memory_format: MemoryFormat::R8g8b8a8,
        texture: BinaryData::from_data([1, 2, 3, 4]).unwrap(),
        delay: None.into(),
        details: Default::default(),
    };
    assert!(matches!(
        icc::apply_transformation(b"invalid", &mut frame, &[1, 2, 3, 4]),
        Err(Error::IccProfile(_))
    ));
    assert_eq!(frame.stride, 4);
    assert_eq!(frame.memory_format, MemoryFormat::R8g8b8a8);
    println!(
        "{{\"channel_order\":true,\"gray_alpha\":true,\"zero_alpha\":true,\"associated_u8\":true,\"associated_u16\":true,\"associated_f32\":true,\"padded_two_rows\":true,\"invalid_profile_transactional\":true,\"rgba8\":{:?},\"rgba16\":{:?},\"rgba32\":{:?}}}",
        half_pixels(&expected),
        floats(&expected16),
        floats(&expected32)
    );
}
