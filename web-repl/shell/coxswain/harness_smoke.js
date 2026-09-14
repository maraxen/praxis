// Coxswain W1.0 harness proof: a deliberately trivial DOM-free module.
// Its only job is to prove that `bun test web-repl/shell/coxswain` discovers
// and runs tests under this directory with no package.json and no bundler,
// locally and in the repl.yml `coxswain` CI job. Real Coxswain modules
// (envelope.js, timing.js) land here in W1 and will be exercised by this same
// harness, which is why it must be proven before anything depends on it.
export function add(a, b) {
  return a + b;
}
