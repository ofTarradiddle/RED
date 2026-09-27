import Foundation
import CryptoKit

/// The manifest is generated during the app build, then protected by app
/// signing alongside its resources. Never use an untrusted remote manifest to
/// authenticate data. A missing, stale or malformed bundle simply uses the
/// engine's normal full edition calculation.
public struct AnnualBundleManifest: Decodable {
    public let schemaVersion: Int
    public let engineVersion: Int
    public let datasetId: String
    public let engineSha256: String
    public let datasetSha256: String
    public let manifestSha256: String

    public static func verifiedDatasetID(manifestData: Data?, engineData: Data,
                                         datasetData: Data, engineVersion: Int) -> String? {
        guard let manifestData, manifestData.count <= 4096,
              let manifest = try? JSONDecoder().decode(Self.self, from: manifestData),
              manifest.schemaVersion == 1, manifest.engineVersion == engineVersion,
              engineVersion == 1,
              manifest.datasetId.range(of: "^annual-v1-[a-f0-9]{16}$", options: .regularExpression) != nil,
              [manifest.engineSha256, manifest.datasetSha256, manifest.manifestSha256].allSatisfy({
                  $0.range(of: "^[a-f0-9]{64}$", options: .regularExpression) != nil
              }) else { return nil }
        let checksumText = [String(manifest.schemaVersion), String(manifest.engineVersion), manifest.datasetId,
                            manifest.engineSha256, manifest.datasetSha256, ""].joined(separator: "\n")
        guard digest(Data(checksumText.utf8)) == manifest.manifestSha256,
              digest(engineData) == manifest.engineSha256,
              digest(datasetData) == manifest.datasetSha256 else { return nil }
        return manifest.datasetId
    }

    private static func digest(_ bytes: Data) -> String {
        SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined()
    }
}
