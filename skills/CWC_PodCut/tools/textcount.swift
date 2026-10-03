import Foundation
import Vision
// textcount <width> <height>   - reads raw BGRA frames on stdin, prints one JSON line per frame:
//   {"n": i, "chars": characters of text Apple Vision reads in the frame, "lines": text lines, "small": characters in
//    lines under 3 % of the frame height (body text, not headlines)}
// Used by CWC_PodCut layout.py to tell a text-heavy screen share (an article, a forum post, a spec list) from a video,
// a photo or a logo (Colden 2026-10-01: "if high density text is on the screen share, do not cut away unless longer").
let W = Int(CommandLine.arguments[1])!, H = Int(CommandLine.arguments[2])!
let frameBytes = W * H * 4
let cs = CGColorSpaceCreateDeviceRGB()
let input = FileHandle.standardInput
var n = 0
while true {
    var data = Data(); data.reserveCapacity(frameBytes)
    while data.count < frameBytes {
        let chunk = input.readData(ofLength: frameBytes - data.count)
        if chunk.isEmpty { break }
        data.append(chunk)
    }
    if data.count < frameBytes { break }
    autoreleasepool {      // per frame, or Vision's objects pile up over a long run
        var chars = 0, lines = 0, small = 0
        if let provider = CGDataProvider(data: data as CFData),
           let cg = CGImage(width: W, height: H, bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: W * 4, space: cs,
                            bitmapInfo: CGBitmapInfo(rawValue: CGImageAlphaInfo.noneSkipFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue),
                            provider: provider, decode: nil, shouldInterpolate: false, intent: .defaultIntent) {
            let req = VNRecognizeTextRequest(); req.recognitionLevel = .fast; req.usesLanguageCorrection = false
            try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
            for o in req.results ?? [] {
                guard let c = o.topCandidates(1).first else { continue }
                let k = c.string.filter { !$0.isWhitespace }.count
                chars += k; lines += 1
                if o.boundingBox.height < 0.03 { small += k }
            }
        }
        print("{\"n\":\(n),\"chars\":\(chars),\"lines\":\(lines),\"small\":\(small)}")
    }
    n += 1
    if n % 10 == 0 { fflush(stdout) }
}
fflush(stdout)
