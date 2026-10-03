// ocr: macOS Vision text recognition -> JSON lines of {file,w,h,words:[{text,x,y,w,h}]} in pixel coords (origin top-left)
import Foundation
import Vision
import AppKit
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("{\"file\":\"\(path)\",\"error\":\"load\"}"); continue }
    let W = CGFloat(cg.width), H = CGFloat(cg.height)
    let req = VNRecognizeTextRequest(); req.recognitionLevel = .accurate; req.usesLanguageCorrection = true
    let handler = VNImageRequestHandler(cgImage: cg, options: [:])
    try? handler.perform([req])
    var items: [String] = []
    for obs in req.results ?? [] {
        guard let cand = obs.topCandidates(1).first else { continue }
        let b = obs.boundingBox
        let x = Int(b.minX * W), y = Int((1 - b.maxY) * H), w = Int(b.width * W), h = Int(b.height * H)
        let t = cand.string.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "\"", with: "\\\"")
        items.append("{\"text\":\"\(t)\",\"x\":\(x),\"y\":\(y),\"w\":\(w),\"h\":\(h)}")
    }
    print("{\"file\":\"\(path)\",\"w\":\(Int(W)),\"h\":\(Int(H)),\"lines\":[\(items.joined(separator: ","))]}")
}
