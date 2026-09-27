// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "REDICore",
    platforms: [.iOS(.v17), .macOS(.v13)],
    products: [.library(name: "REDICore", targets: ["REDICore"])],
    targets: [
        .target(name: "REDICore"),
        .testTarget(name: "REDICoreTests", dependencies: ["REDICore"])
    ]
)
