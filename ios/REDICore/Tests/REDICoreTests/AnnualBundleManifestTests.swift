import XCTest
import CryptoKit
@testable import REDICore

final class AnnualBundleManifestTests: XCTestCase {
    private let engine = Data("verified engine bytes\n".utf8)
    private let dataset = Data("{\"observedPrice\":123.5}\n".utf8)
    private let edition = "annual-v1-1234567890abcdef"

    private func digest(_ value: Data) -> String {
        SHA256.hash(data: value).map { String(format: "%02x", $0) }.joined()
    }
    private func manifest() -> [String: Any] {
        let engineHash = digest(engine), dataHash = digest(dataset)
        let seal = "1\n1\n\(edition)\n\(engineHash)\n\(dataHash)\n"
        return ["schemaVersion": 1, "engineVersion": 1, "datasetId": edition,
                "engineSha256": engineHash, "datasetSha256": dataHash,
                "manifestSha256": digest(Data(seal.utf8))]
    }
    private func encoded(_ value: [String: Any]) throws -> Data {
        try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    }
    func testExactBundledBytesUseTheOriginalEdition() throws {
        XCTAssertEqual(AnnualBundleManifest.verifiedDatasetID(manifestData: try encoded(manifest()),
            engineData: engine, datasetData: dataset, engineVersion: 1), edition)
    }
    func testAChangedPriceOrEngineFallsBackRatherThanReusingAnEdition() throws {
        let saved = try encoded(manifest())
        XCTAssertNil(AnnualBundleManifest.verifiedDatasetID(manifestData: saved,
            engineData: engine, datasetData: Data("{\"observedPrice\":124.5}\n".utf8), engineVersion: 1))
        XCTAssertNil(AnnualBundleManifest.verifiedDatasetID(manifestData: saved,
            engineData: engine + Data("changed rules".utf8), datasetData: dataset, engineVersion: 1))
        XCTAssertNil(AnnualBundleManifest.verifiedDatasetID(manifestData: saved,
            engineData: engine, datasetData: dataset, engineVersion: 2))
    }
    func testMissingMalformedAndEditedManifestsFallBack() throws {
        for bytes in [nil, Data(), Data("not JSON".utf8), Data(repeating: 32, count: 4097)] as [Data?] {
            XCTAssertNil(AnnualBundleManifest.verifiedDatasetID(manifestData: bytes,
                engineData: engine, datasetData: dataset, engineVersion: 1))
        }
        for (key, replacement) in [("datasetId", "annual-v1-0000000000000000"),
                                    ("datasetSha256", String(repeating: "a", count: 64)),
                                    ("manifestSha256", "not-a-hash")] {
            var edited = manifest(); edited[key] = replacement
            XCTAssertNil(AnnualBundleManifest.verifiedDatasetID(manifestData: try encoded(edited),
                engineData: engine, datasetData: dataset, engineVersion: 1))
        }
    }
}
