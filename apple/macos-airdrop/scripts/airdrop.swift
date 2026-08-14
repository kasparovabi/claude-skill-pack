import Cocoa

let path = CommandLine.arguments[1]
let url = URL(fileURLWithPath: path)

guard let service = NSSharingService(named: NSSharingService.Name(rawValue: "com.apple.share.AirDrop.send")) else {
    print("AirDrop service unavailable"); exit(1)
}

class D: NSObject, NSSharingServiceDelegate {
    func sharingService(_ s: NSSharingService, didFailToShareItems items: [Any], error: Error) {
        print("FAIL: \(error.localizedDescription)"); NSApplication.shared.terminate(nil)
    }
    func sharingService(_ s: NSSharingService, didShareItems items: [Any]) {
        print("SHARED"); NSApplication.shared.terminate(nil)
    }
}
let d = D()
service.delegate = d

let app = NSApplication.shared
app.setActivationPolicy(.regular)
app.activate(ignoringOtherApps: true)

DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
    if service.canPerform(withItems: [url]) {
        service.perform(withItems: [url])
    } else {
        print("cannot perform"); exit(2)
    }
}

app.run()
