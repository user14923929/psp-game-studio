// Thin front-end: every command shells out to the `pocketpsp` CLI.
// No compiler or build logic lives here.
import * as vscode from "vscode";
import { execFile } from "child_process";

interface CliDiagnostic {
  message: string;
  file: string | null;
  line: number | null;
  column: number | null;
  severity: string;
}

function exe(): string {
  return vscode.workspace.getConfiguration("pocketpsp").get<string>("executable") || "pocketpsp";
}

function projectDir(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

function runInTerminal(args: string[]): void {
  const dir = projectDir();
  if (!dir) {
    vscode.window.showErrorMessage("Open a PSP project folder first.");
    return;
  }
  const term = vscode.window.createTerminal({ name: "PSP Game Studio", cwd: dir });
  term.show();
  term.sendText([exe(), ...args].map((a) => JSON.stringify(a)).join(" "));
}

function check(diags: vscode.DiagnosticCollection): void {
  const dir = projectDir();
  if (!dir) {
    return;
  }
  execFile(exe(), ["-C", dir, "check", "--format", "json"], (err, stdout, stderr) => {
    diags.clear();
    if (err && !stdout) {
      vscode.window.showErrorMessage(`pocketpsp failed: ${stderr || err.message}`);
      return;
    }
    let items: CliDiagnostic[] = [];
    try {
      items = JSON.parse(stdout) as CliDiagnostic[];
    } catch {
      return; // not JSON: e.g. project.toml errors are reported on stderr
    }
    const byFile = new Map<string, vscode.Diagnostic[]>();
    for (const d of items) {
      const file = vscode.Uri.file(require("path").resolve(dir, d.file ?? "game.py")).toString();
      const line = Math.max((d.line ?? 1) - 1, 0);
      const col = Math.max((d.column ?? 1) - 1, 0);
      const diag = new vscode.Diagnostic(
        new vscode.Range(line, col, line, Number.MAX_SAFE_INTEGER),
        d.message,
        d.severity === "error" ? vscode.DiagnosticSeverity.Error : vscode.DiagnosticSeverity.Warning,
      );
      diag.source = "pocketpsp";
      byFile.set(file, [...(byFile.get(file) ?? []), diag]);
    }
    for (const [uri, list] of byFile) {
      diags.set(vscode.Uri.parse(uri), list);
    }
  });
}

export function activate(context: vscode.ExtensionContext): void {
  const diags = vscode.languages.createDiagnosticCollection("pocketpsp");
  context.subscriptions.push(
    diags,
    vscode.commands.registerCommand("pocketpsp.build", () => runInTerminal(["build"])),
    vscode.commands.registerCommand("pocketpsp.run", () => runInTerminal(["run"])),
    vscode.commands.registerCommand("pocketpsp.check", () => check(diags)),
    vscode.commands.registerCommand("pocketpsp.new", async () => {
      const name = await vscode.window.showInputBox({ prompt: "Project name" });
      const dir = projectDir();
      if (name && dir) {
        const term = vscode.window.createTerminal({ name: "PSP Game Studio", cwd: dir });
        term.show();
        term.sendText(`${JSON.stringify(exe())} new ${JSON.stringify(name)}`);
      }
    }),
    vscode.workspace.onDidSaveTextDocument((doc) => {
      if (doc.languageId === "python") {
        check(diags);
      }
    }),
  );
  check(diags);
}

export function deactivate(): void {}
