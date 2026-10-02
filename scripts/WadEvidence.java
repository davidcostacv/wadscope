// Export bounded, string-linked static-analysis evidence from the current program.
// Invoke after analysis: -postScript WadEvidence.java <ignored-output-directory> [function-entry ...]
// This original script does not assign engine-source names to discovered functions.
// @category Research

import java.io.BufferedWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class WadEvidence extends GhidraScript {
    private static final int MAX_STRINGS = 100;
    private static final int MAX_REFERENCES_PER_STRING = 64;
    private static final int MAX_FUNCTIONS = 20;
    private static final int MAX_REQUESTED_FUNCTIONS = 20;
    private static final int MAX_INSTRUCTIONS_PER_FUNCTION = 300;
    private static final int DECOMPILE_TIMEOUT_SECONDS = 30;
    private static final String[] ANCHORS = {
        "W_AddFile", "W_ReadLump", "W_GetNumForName", "IWAD", "PWAD", "lump"
    };

    private static class StringHit {
        Address address;
        String value;
        String anchors;
        int priority;
    }

    private static class Candidate {
        Function function;
        int priority;
        Set<String> reasons = new LinkedHashSet<>();
    }

    private static String field(String value) {
        if (value == null) return "";
        return value.replace("\\", "\\\\").replace("\t", "\\t")
            .replace("\r", "\\r").replace("\n", "\\n");
    }

    private static BufferedWriter writer(Path path) throws Exception {
        return Files.newBufferedWriter(path, StandardCharsets.UTF_8);
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1 || args.length > MAX_REQUESTED_FUNCTIONS + 1 || args[0].trim().isEmpty()) {
            throw new IllegalArgumentException("Expected output directory and at most "
                + MAX_REQUESTED_FUNCTIONS + " optional exact function-entry addresses.");
        }
        if (currentProgram == null) throw new IllegalStateException("No current program.");
        List<Function> requestedFunctions = new ArrayList<>();
        for (int i = 1; i < args.length; i++) {
            monitor.checkCancelled();
            Address entry = toAddr(args[i]);
            Function function = entry == null ? null : currentProgram.getFunctionManager().getFunctionAt(entry);
            if (function == null) {
                throw new IllegalArgumentException("Requested address is not an exact existing function entry: " + args[i]);
            }
            requestedFunctions.add(function);
        }
        Path output = Paths.get(args[0]).toAbsolutePath().normalize();
        Files.createDirectories(output);

        // Prefer named loader anchors over the much broader word 'lump'. Ties use
        // addresses, so the bounded selection is reproducible for the same analysis.
        Comparator<StringHit> order = Comparator
            .comparingInt((StringHit h) -> h.priority).reversed()
            .thenComparing(h -> h.address);
        TreeSet<StringHit> hits = new TreeSet<>(order);
        int matchingStrings = 0;
        DataIterator data = currentProgram.getListing().getDefinedData(true);
        while (data.hasNext()) {
            monitor.checkCancelled();
            Data item = data.next();
            Object value = item.getValue();
            if (!(value instanceof String)) continue;
            String text = (String) value;
            String lower = text.toLowerCase(Locale.ROOT);
            List<String> anchors = new ArrayList<>();
            int priority = 0;
            for (int i = 0; i < ANCHORS.length; i++) {
                if (lower.contains(ANCHORS[i].toLowerCase(Locale.ROOT))) {
                    anchors.add(ANCHORS[i]);
                    priority = Math.max(priority, i < 3 ? 3 : i < 5 ? 2 : 1);
                }
            }
            if (anchors.isEmpty()) continue;
            matchingStrings++;
            StringHit hit = new StringHit();
            hit.address = item.getAddress();
            hit.value = text;
            hit.anchors = String.join(",", anchors);
            hit.priority = priority;
            hits.add(hit);
            if (hits.size() > MAX_STRINGS) hits.pollLast();
        }

        Map<Address, Candidate> candidates = new TreeMap<>();
        int cappedReferenceStrings = 0;
        try (BufferedWriter strings = writer(output.resolve("strings.tsv"));
                BufferedWriter refs = writer(output.resolve("references.tsv"))) {
            strings.write("address\tanchors\tpriority\tvalue\n");
            refs.write("string_address\tfrom_address\treference_type\tis_code\tfunction_entry\tfunction_name\n");
            for (StringHit hit : hits) {
                monitor.checkCancelled();
                strings.write(hit.address + "\t" + hit.anchors + "\t" + hit.priority + "\t" + field(hit.value) + "\n");
                ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(hit.address);
                int count = 0;
                while (references.hasNext() && count < MAX_REFERENCES_PER_STRING) {
                    monitor.checkCancelled();
                    Reference ref = references.next();
                    count++;
                    Address from = ref.getFromAddress();
                    boolean code = currentProgram.getListing().getInstructionContaining(from) != null;
                    Function function = code ? currentProgram.getFunctionManager().getFunctionContaining(from) : null;
                    refs.write(hit.address + "\t" + from + "\t" + field(ref.getReferenceType().toString())
                        + "\t" + code + "\t" + (function == null ? "" : function.getEntryPoint())
                        + "\t" + (function == null ? "" : field(function.getName())) + "\n");
                    if (function != null) {
                        Candidate candidate = candidates.get(function.getEntryPoint());
                        if (candidate == null) {
                            candidate = new Candidate();
                            candidate.function = function;
                            candidates.put(function.getEntryPoint(), candidate);
                        }
                        candidate.priority = Math.max(candidate.priority, hit.priority);
                        candidate.reasons.add("code reference " + from + " to string " + hit.address + " [" + hit.anchors + "]");
                    }
                }
                if (references.hasNext()) cappedReferenceStrings++;
            }
        }

        int discoveredFunctions = candidates.size();
        for (Function function : requestedFunctions) {
            Candidate candidate = candidates.get(function.getEntryPoint());
            if (candidate == null) {
                candidate = new Candidate();
                candidate.function = function;
                candidates.put(function.getEntryPoint(), candidate);
            }
            candidate.priority = 4;
            candidate.reasons.add("manually selected function entry");
        }
        List<Candidate> selected = new ArrayList<>(candidates.values());
        selected.sort(Comparator.comparingInt((Candidate c) -> c.priority).reversed()
            .thenComparing(c -> c.function.getEntryPoint()));
        if (selected.size() > MAX_FUNCTIONS) selected = selected.subList(0, MAX_FUNCTIONS);

        DecompInterface decompiler = new DecompInterface();
        try (BufferedWriter manifest = writer(output.resolve("functions.tsv"))) {
            manifest.write("entry\tname\tpriority\tstatus\tdecompiled_file\tdisassembly_file\tdisassembly_truncated\treason\terror\n");
            if (!decompiler.openProgram(currentProgram)) {
                throw new IllegalStateException("Cannot initialize decompiler: " + decompiler.getLastMessage());
            }
            for (Candidate candidate : selected) {
                monitor.checkCancelled();
                Function function = candidate.function;
                String stem = function.getEntryPoint().toString().replaceAll("[^A-Za-z0-9_-]", "_");
                String cFile = stem + ".c.txt";
                String asmFile = stem + ".asm.txt";
                DecompileResults result = decompiler.decompileFunction(function, DECOMPILE_TIMEOUT_SECONDS, monitor);
                String status = result.decompileCompleted() && result.getDecompiledFunction() != null ? "completed" : "failed";
                try (BufferedWriter decompiled = writer(output.resolve(cFile))) {
                    decompiled.write("/* Ghidra candidate at " + function.getEntryPoint()
                        + "; linkage is a research lead, not a verified source identity. */\n");
                    if (status.equals("completed")) decompiled.write(result.getDecompiledFunction().getC());
                    else decompiled.write("/* Decompilation failed: " + field(result.getErrorMessage()).replace("*/", "* /") + " */\n");
                }
                boolean truncated;
                try (BufferedWriter assembly = writer(output.resolve(asmFile))) {
                    assembly.write("# Candidate " + function.getEntryPoint() + " " + field(function.getName()) + "\n");
                    InstructionIterator instructions = currentProgram.getListing().getInstructions(function.getBody(), true);
                    int count = 0;
                    while (instructions.hasNext() && count < MAX_INSTRUCTIONS_PER_FUNCTION) {
                        monitor.checkCancelled();
                        Instruction instruction = instructions.next();
                        assembly.write(instruction.getAddress() + "\t" + instruction.toString() + "\n");
                        count++;
                    }
                    truncated = instructions.hasNext();
                    if (truncated) assembly.write("# Instruction cap reached.\n");
                }
                manifest.write(function.getEntryPoint() + "\t" + field(function.getName()) + "\t" + candidate.priority
                    + "\t" + status + "\t" + cFile + "\t" + asmFile + "\t" + truncated
                    + "\t" + field(String.join("; ", candidate.reasons)) + "\t" + field(result.getErrorMessage()) + "\n");
                println("Candidate " + function.getEntryPoint() + ": " + status + "; " + output.resolve(cFile));
            }
        } finally {
            decompiler.dispose();
        }

        try (BufferedWriter metadata = writer(output.resolve("run.tsv"))) {
            metadata.write("key\tvalue\n");
            metadata.write("program\t" + field(currentProgram.getName()) + "\n");
            metadata.write("executable_sha256\t" + field(currentProgram.getExecutableSHA256()) + "\n");
            metadata.write("language\t" + field(currentProgram.getLanguageID().toString()) + "\n");
            metadata.write("compiler_spec\t" + field(currentProgram.getCompilerSpec().getCompilerSpecID().toString()) + "\n");
            metadata.write("matching_defined_strings\t" + matchingStrings + "\n");
            metadata.write("exported_strings\t" + hits.size() + "\n");
            metadata.write("reference_capped_strings\t" + cappedReferenceStrings + "\n");
            metadata.write("discovered_candidate_functions\t" + discoveredFunctions + "\n");
            metadata.write("exported_candidate_functions\t" + selected.size() + "\n");
            metadata.write("requested_function_addresses\t" + requestedFunctions.size() + "\n");
            metadata.write("max_strings\t" + MAX_STRINGS + "\n");
            metadata.write("max_references_per_string\t" + MAX_REFERENCES_PER_STRING + "\n");
            metadata.write("max_functions\t" + MAX_FUNCTIONS + "\n");
            metadata.write("max_requested_functions\t" + MAX_REQUESTED_FUNCTIONS + "\n");
            metadata.write("max_instructions_per_function\t" + MAX_INSTRUCTIONS_PER_FUNCTION + "\n");
            metadata.write("decompile_timeout_seconds\t" + DECOMPILE_TIMEOUT_SECONDS + "\n");
            metadata.write("scope\tDefined string values; direct references to string starts; existing containing functions and optionally requested exact function entries only. No indirect-reference or call-graph traversal.\n");
            metadata.write("interpretation\tCandidate linkage only; generated names and decompilation are not verified engine source or exact original C.\n");
        }
        println("Exported " + hits.size() + " strings and " + selected.size() + " candidate functions to " + output);
    }
}
