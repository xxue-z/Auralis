const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const version = process.argv[2];

if (!version) {
    console.error('Usage: node scripts/inject-version.js <version>');
    process.exit(1);
}

const confPath = path.join(root, 'src-tauri', 'tauri.conf.json');
let conf = JSON.parse(fs.readFileSync(confPath, 'utf8'));
conf.version = version;
fs.writeFileSync(confPath, JSON.stringify(conf, null, 2) + '\n');
console.log('Updated tauri.conf.json version -> ' + version);

const cargoPath = path.join(root, 'src-tauri', 'Cargo.toml');
let cargo = fs.readFileSync(cargoPath, 'utf8');
cargo = cargo.replace(/^version = ".*"/m, 'version = "' + version + '"');
fs.writeFileSync(cargoPath, cargo);
console.log('Updated Cargo.toml version -> ' + version);
