import qrcode from "qrcode-generator";

function fixedProfile(
  id,
  name,
  width,
  height,
  printableWidth,
  printableHeight,
  qrSize,
  page = false,
) {
  return {
    id,
    name,
    media_type: "fixed",
    width_mm: width,
    height_mm: height,
    printable_width_mm: printableWidth,
    printable_height_mm: printableHeight,
    dpi: page ? 300 : 203,
    max_qr_size_mm: qrSize,
    alignment: page ? "start" : "center",
    min_module_dots: 3,
  };
}

export const BUILTIN_LABEL_PROFILES = [
  {
    id: "tape-24mm",
    name: "24 mm tape — 18 mm printable",
    media_type: "continuous",
    width_mm: 24,
    printable_width_mm: 18,
    dpi: 180,
    max_qr_size_mm: 18,
    alignment: "center",
    min_module_dots: 3,
  },
  {
    id: "tape-36mm",
    name: "36 mm tape — 27 mm printable",
    media_type: "continuous",
    width_mm: 36,
    printable_width_mm: 27,
    dpi: 180,
    max_qr_size_mm: 27,
    alignment: "center",
    min_module_dots: 3,
  },
  fixedProfile("label-25x25mm", "25 × 25 mm square label", 25, 25, 21, 21, 15),
  fixedProfile("label-30x20mm", "30 × 20 mm small label", 30, 20, 26, 16, 10),
  fixedProfile("label-50x30mm", "50 × 30 mm standard label", 50, 30, 46, 26, 20),
  fixedProfile("label-50x50mm", "50 × 50 mm square label", 50, 50, 46, 46, 30),
  fixedProfile("label-70x40mm", "70 × 40 mm large label", 70, 40, 66, 36, 30),
  fixedProfile("label-100x50mm", "100 × 50 mm wide label", 100, 50, 96, 46, 30),
  fixedProfile("a6-single", "A6 page", 105, 148, 85, 128, 30, true),
  fixedProfile("a4-single", "A4 page", 210, 297, 190, 277, 30, true),
];

export function makeQRCode(value) {
  const code = qrcode(0, "Q");
  code.addData(value, "Byte");
  code.make();
  const svg = code.createSvgTag({ cellSize: 1, margin: 4, scalable: true });
  return {
    image: `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`,
    modules: code.getModuleCount() + 8,
  };
}

export function dotsPerModule(profile, modules) {
  return Math.floor((profile.max_qr_size_mm * profile.dpi) / 25.4 / modules);
}
