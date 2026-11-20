import AppKit
import Foundation

let source = URL(fileURLWithPath: CommandLine.arguments[1])
let output = URL(fileURLWithPath: CommandLine.arguments[2])
let fm = FileManager.default
try fm.createDirectory(at: output, withIntermediateDirectories: true)
func image(_ name: String) -> NSImage { NSImage(contentsOf: source.appendingPathComponent(name))! }
let app = image("App2.png"), logo = image("Logo.png"), brand = image("Brand.png")
func write(_ image: NSImage, _ width: Int, _ height: Int, _ path: String) throws {
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: width, pixelsHigh: height, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
    NSGraphicsContext.current!.imageInterpolation = .high
    NSColor.clear.setFill(); NSRect(x: 0, y: 0, width: width, height: height).fill()
    let scale = min(CGFloat(width)/image.size.width, CGFloat(height)/image.size.height)
    let w = image.size.width*scale, h = image.size.height*scale
    image.draw(in: NSRect(x: (CGFloat(width)-w)/2, y: (CGFloat(height)-h)/2, width: w, height: h), from: .zero, operation: .copy, fraction: 1, respectFlipped: true, hints: [.interpolation: NSImageInterpolation.high])
    NSGraphicsContext.restoreGraphicsState()
    let dest = output.appendingPathComponent(path)
    try fm.createDirectory(at: dest.deletingLastPathComponent(), withIntermediateDirectories: true)
    try bitmap.representation(using: .png, properties: [:])!.write(to: dest)
}
for n in [16,32,48,128,192,256,512,1024] { try write(logo,n,n,"symbol-\(n).png") }
for n in [16,32,48,128,180,192,256,512,1024] { try write(app,n,n,"app-\(n).png") }
try write(brand,1200,400,"brand-og.png")
for n in [16,32,128,256,512] {
    try write(app,n,n,"NoYouPub.iconset/icon_\(n)x\(n).png")
    try write(app,n*2,n*2,"NoYouPub.iconset/icon_\(n)x\(n)@2x.png")
}
for name in ["App2.png","Logo.png","Brand.png"] {
    let b = NSBitmapImageRep(data: try Data(contentsOf: source.appendingPathComponent(name)))!
    var minAlpha: CGFloat = 1, maxAlpha: CGFloat = 0
    for y in stride(from: 0, to: b.pixelsHigh, by: 3) { for x in stride(from: 0, to: b.pixelsWide, by: 3) {
        let a = b.colorAt(x: x,y: y)!.alphaComponent; minAlpha = min(minAlpha,a); maxAlpha = max(maxAlpha,a)
    }}
    print("\(name): \(b.pixelsWide)x\(b.pixelsHigh), alpha \(minAlpha)...\(maxAlpha), corner alpha \(b.colorAt(x: 0,y: 0)!.alphaComponent)")
}
