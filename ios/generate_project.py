"""Generate the small native Xcode project without a third-party generator."""
from hashlib import sha1
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
objects = {}


def add(key, isa, **fields):
    ref = sha1(key.encode()).hexdigest()[:24].upper()
    objects[ref] = dict(isa=isa, **fields)
    return ref


def ref(key):
    return sha1(key.encode()).hexdigest()[:24].upper()


def serialize(value, depth=0):
    if isinstance(value, dict):
        return '{\n' + ''.join('\t' * (depth + 1) + json.dumps(k) + ' = ' + serialize(v, depth + 1) + ';\n' for k, v in value.items()) + '\t' * depth + '}'
    if isinstance(value, list):
        return '(' + ', '.join(serialize(item, depth) for item in value) + (',' if value else '') + ')'
    return str(value) if isinstance(value, int) else json.dumps(value)


def file(path, kind):
    return add('file:' + path, 'PBXFileReference', lastKnownFileType=kind, path=path, sourceTree='<group>')


def phase(name, isa, files):
    return add(name, isa, buildActionMask=2147483647, files=files, runOnlyForDeploymentPostprocessing=0)


swift = ['REDICompareApp.swift', 'ComparisonStore.swift', 'Theme.swift', 'Views.swift', 'ArcadeStore.swift', 'ArcadeViews.swift', 'ResearchViews.swift', 'AnnualGameStore.swift', 'AnnualGameViews.swift']
source_refs = [file(name, 'sourcecode.swift') for name in swift]
source_builds = [add('source:' + name, 'PBXBuildFile', fileRef=identifier) for name, identifier in zip(swift, source_refs)]
resource_names = [('Assets.xcassets', 'folder.assetcatalog'), ('PrivacyInfo.xcprivacy', 'text.xml'), ('comparison-preview.json', 'text.json'), ('../../assets/innovation-game-engine.js', 'sourcecode.javascript'), ('../../assets/innovation-arcade-engine.js', 'sourcecode.javascript'), ('../../assets/annual-portfolio-engine.js', 'sourcecode.javascript'), ('../../data/innovation/dataset.json', 'text.json'), ('../../data/strategy_research.json', 'text.json')]
resource_refs = [file(name, kind) for name, kind in resource_names]
resource_builds = [add('resource:' + name, 'PBXBuildFile', fileRef=identifier) for (name, _), identifier in zip(resource_names, resource_refs)]
info = file('Info.plist', 'text.plist.xml')
app_group = add('app-group', 'PBXGroup', children=source_refs + resource_refs + [info], path='REDICompare', sourceTree='<group>')
test_file = file('REDICompareUITests.swift', 'sourcecode.swift')
test_group = add('test-group', 'PBXGroup', children=[test_file], path='REDICompareUITests', sourceTree='<group>')
app_product = add('app-product', 'PBXFileReference', explicitFileType='wrapper.application', includeInIndex=0, path='REDICompare.app', sourceTree='BUILT_PRODUCTS_DIR')
test_product = add('test-product', 'PBXFileReference', explicitFileType='wrapper.cfbundle', includeInIndex=0, path='REDICompareUITests.xctest', sourceTree='BUILT_PRODUCTS_DIR')
products_group = add('products-group', 'PBXGroup', children=[app_product, test_product], name='Products', sourceTree='<group>')
main_group = add('main-group', 'PBXGroup', children=[app_group, test_group, products_group], sourceTree='<group>')
package = add('core-package', 'XCLocalSwiftPackageReference', relativePath='REDICore')
dependency = add('core-product', 'XCSwiftPackageProductDependency', package=package, productName='REDICore')
framework = add('core-framework', 'PBXBuildFile', productRef=dependency)

project_settings = {
    'CLANG_ENABLE_MODULES': 'YES', 'SWIFT_VERSION': '5.0', 'IPHONEOS_DEPLOYMENT_TARGET': '17.0',
    'SDKROOT': 'iphoneos', 'CODE_SIGN_STYLE': 'Automatic', 'DEVELOPMENT_TEAM': '',
    'MARKETING_VERSION': '1.0', 'CURRENT_PROJECT_VERSION': '2', 'ENABLE_USER_SCRIPT_SANDBOXING': 'YES',
    'CLANG_WARN_DOCUMENTATION_COMMENTS': 'YES', 'GCC_C_LANGUAGE_STANDARD': 'gnu17',
    # Xcode launched from Finder does not inherit a shell's Node path. Override
    # this setting with an absolute installed Node executable when needed.
    'ANNUAL_NODE_BINARY': '/opt/homebrew/bin/node',
}
project_configs = []
app_configs = []
test_configs = []
for name in ('Debug', 'Release'):
    debug = name == 'Debug'
    settings = dict(project_settings, SWIFT_OPTIMIZATION_LEVEL='-Onone' if debug else '-O',
                    ONLY_ACTIVE_ARCH='YES' if debug else 'NO',
                    DEBUG_INFORMATION_FORMAT='dwarf' if debug else 'dwarf-with-dsym',
                    ENABLE_TESTABILITY='YES' if debug else 'NO',
                    SWIFT_ACTIVE_COMPILATION_CONDITIONS='DEBUG' if debug else '')
    project_configs.append(add('project-' + name, 'XCBuildConfiguration', name=name, buildSettings=settings))
    app_settings = dict(PRODUCT_BUNDLE_IDENTIFIER='com.hetzerk.REDIPlay', PRODUCT_NAME='$(TARGET_NAME)',
                        INFOPLIST_FILE='REDICompare/Info.plist', ASSETCATALOG_COMPILER_APPICON_NAME='AppIcon',
                        ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME='AccentColor', TARGETED_DEVICE_FAMILY='1,2',
                        SUPPORTED_PLATFORMS='iphoneos iphonesimulator', SUPPORTS_MACCATALYST='NO',
                        LD_RUNPATH_SEARCH_PATHS=['$(inherited)', '@executable_path/Frameworks'])
    if not debug:
        app_settings['EXCLUDED_SOURCE_FILE_NAMES'] = 'comparison-preview.json'
    app_configs.append(add('app-' + name, 'XCBuildConfiguration', name=name, buildSettings=app_settings))
    test_settings = dict(PRODUCT_BUNDLE_IDENTIFIER='com.hetzerk.REDICompareUITests', PRODUCT_NAME='$(TARGET_NAME)',
                         GENERATE_INFOPLIST_FILE='YES', TARGETED_DEVICE_FAMILY='1,2', TEST_TARGET_NAME='REDICompare',
                         LD_RUNPATH_SEARCH_PATHS=['$(inherited)', '@executable_path/Frameworks', '@loader_path/Frameworks'])
    test_configs.append(add('tests-' + name, 'XCBuildConfiguration', name=name, buildSettings=test_settings))


def configurations(key, configs):
    return add(key, 'XCConfigurationList', buildConfigurations=configs, defaultConfigurationIsVisible=0, defaultConfigurationName='Release')


annual_resource = add('annual-resource-copy', 'PBXShellScriptBuildPhase', name='Bundle annual portfolio source',
                      buildActionMask=2147483647, files=[], runOnlyForDeploymentPostprocessing=0,
                      inputPaths=['$(SRCROOT)/../data/annual-game/dataset.json',
                                  '$(TARGET_BUILD_DIR)/$(UNLOCALIZED_RESOURCES_FOLDER_PATH)/annual-portfolio-engine.js',
                                  '$(SRCROOT)/generate_annual_manifest.cjs', '$(ANNUAL_NODE_BINARY)'],
                      outputPaths=['$(TARGET_BUILD_DIR)/$(UNLOCALIZED_RESOURCES_FOLDER_PATH)/annual-game.json',
                                   '$(TARGET_BUILD_DIR)/$(UNLOCALIZED_RESOURCES_FOLDER_PATH)/annual-game-manifest.json'],
                      shellPath='/bin/sh',
                      shellScript='set -eu\n/bin/cp "${SCRIPT_INPUT_FILE_0}" "${SCRIPT_OUTPUT_FILE_0}"\n'
                                  '"${SCRIPT_INPUT_FILE_3}" "${SCRIPT_INPUT_FILE_2}" "${SCRIPT_INPUT_FILE_1}" "${SCRIPT_OUTPUT_FILE_0}" "${SCRIPT_OUTPUT_FILE_1}"\n')

app_target = add('app-target', 'PBXNativeTarget', buildConfigurationList=configurations('app-configs', app_configs),
                 buildPhases=[phase('app-sources', 'PBXSourcesBuildPhase', source_builds),
                              phase('app-frameworks', 'PBXFrameworksBuildPhase', [framework]),
                              phase('app-resources', 'PBXResourcesBuildPhase', resource_builds), annual_resource],
                 buildRules=[], dependencies=[], name='REDICompare', productName='REDICompare',
                 productReference=app_product, productType='com.apple.product-type.application',
                 packageProductDependencies=[dependency])
proxy = add('app-proxy', 'PBXContainerItemProxy', containerPortal=ref('project'), proxyType=1,
            remoteGlobalIDString=app_target, remoteInfo='REDICompare')
test_dependency = add('test-dependency', 'PBXTargetDependency', target=app_target, targetProxy=proxy)
test_target = add('test-target', 'PBXNativeTarget', buildConfigurationList=configurations('test-configs', test_configs),
                  buildPhases=[phase('test-sources', 'PBXSourcesBuildPhase', [add('test-source', 'PBXBuildFile', fileRef=test_file)]),
                               phase('test-frameworks', 'PBXFrameworksBuildPhase', []), phase('test-resources', 'PBXResourcesBuildPhase', [])],
                  buildRules=[], dependencies=[test_dependency], name='REDICompareUITests', productName='REDICompareUITests',
                  productReference=test_product, productType='com.apple.product-type.bundle.ui-testing')
project = add('project', 'PBXProject', attributes={'BuildIndependentTargetsInParallel': 'YES', 'LastSwiftUpdateCheck': '1600',
              'LastUpgradeCheck': '1600', 'TargetAttributes': {app_target: {'CreatedOnToolsVersion': '16.0'}, test_target: {'CreatedOnToolsVersion': '16.0', 'TestTargetID': app_target}}},
              buildConfigurationList=configurations('project-configs', project_configs), compatibilityVersion='Xcode 14.0',
              developmentRegion='en', hasScannedForEncodings=0, knownRegions=['en', 'Base'], mainGroup=main_group,
              productRefGroup=products_group, projectDirPath='', projectRoot='', targets=[app_target, test_target], packageReferences=[package])
bundle = ROOT / 'REDICompare.xcodeproj'
bundle.mkdir(exist_ok=True)
(bundle / 'project.pbxproj').write_text('// !$*UTF8*$!\n' + serialize(dict(archiveVersion=1, classes={}, objectVersion=56, objects=objects, rootObject=project)) + '\n')
schemes = bundle / 'xcshareddata/xcschemes'
schemes.mkdir(parents=True, exist_ok=True)


def build_reference(identifier, name):
    product = name + ('.app' if name == 'REDICompare' else '.xctest')
    return f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{identifier}" BuildableName="{product}" BlueprintName="{name}" ReferencedContainer="container:REDICompare.xcodeproj"/>'


app_reference = build_reference(app_target, 'REDICompare')
test_reference = build_reference(test_target, 'REDICompareUITests')
(schemes / 'REDICompare.xcscheme').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="1600" version="1.3">
  <BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries>
    <BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" buildForArchiving="YES" buildForAnalyzing="YES">{app_reference}</BuildActionEntry>
    <BuildActionEntry buildForTesting="YES" buildForRunning="NO" buildForProfiling="NO" buildForArchiving="NO" buildForAnalyzing="NO">{test_reference}</BuildActionEntry>
  </BuildActionEntries></BuildAction>
  <TestAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" shouldUseLaunchSchemeArgsEnv="YES"><Testables><TestableReference skipped="NO">{test_reference}</TestableReference></Testables></TestAction>
  <LaunchAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" launchStyle="0" useCustomWorkingDirectory="NO" ignoresPersistentStateOnLaunch="NO" debugDocumentVersioning="YES" debugServiceExtension="internal" allowLocationSimulation="YES"><BuildableProductRunnable runnableDebuggingMode="0">{app_reference}</BuildableProductRunnable></LaunchAction>
  <ProfileAction buildConfiguration="Release" shouldUseLaunchSchemeArgsEnv="YES" savedToolIdentifier="" useCustomWorkingDirectory="NO" debugDocumentVersioning="YES"><BuildableProductRunnable runnableDebuggingMode="0">{app_reference}</BuildableProductRunnable></ProfileAction>
  <AnalyzeAction buildConfiguration="Debug"/>
  <ArchiveAction buildConfiguration="Release" revealArchiveInOrganizer="YES"/>
</Scheme>''')
print('Generated', bundle)
