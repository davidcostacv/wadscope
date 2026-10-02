// Enumerate direct references to explicitly supplied map-research function entries.
// @category Research
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.io.BufferedWriter;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class MapCallers extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2 || args.length > 21) {
            throw new IllegalArgumentException("Expected output directory and 1-20 exact function entries.");
        }
        Path output = Paths.get(args[0]).toAbsolutePath().normalize();
        Files.createDirectories(output);
        try (BufferedWriter writer = Files.newBufferedWriter(output.resolve("callers.tsv"), StandardCharsets.UTF_8)) {
            writer.write("target\tfrom\treference_type\tcontaining_function\n");
            for (int i = 1; i < args.length; i++) {
                Address target = toAddr(args[i]);
                if (target == null || currentProgram.getFunctionManager().getFunctionAt(target) == null) {
                    throw new IllegalArgumentException("Not an exact function entry: " + args[i]);
                }
                ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(target);
                int count = 0;
                while (refs.hasNext() && count++ < 100) {
                    monitor.checkCancelled();
                    Reference ref = refs.next();
                    Function caller = currentProgram.getFunctionManager().getFunctionContaining(ref.getFromAddress());
                    writer.write(target + "\t" + ref.getFromAddress() + "\t" + ref.getReferenceType()
                        + "\t" + (caller == null ? "" : caller.getEntryPoint()) + "\n");
                }
                if (refs.hasNext()) writer.write(target + "\t\tTRUNCATED_AT_100\t\n");
            }
        }
        println("Caller evidence: " + output.resolve("callers.tsv"));
    }
}
