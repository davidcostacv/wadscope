// Export bounded map-loader string leads using the shared evidence exporter.
// Invoke after analysis: -postScript MapEvidence.java <ignored-output-directory> [function-entry ...]
// @category Research

public class MapEvidence extends WadEvidence {
    @Override
    protected String[] anchorTerms() {
        return new String[] {
            "P_LoadVertexes", "P_LoadLineDefs", "P_LoadThings", "P_LoadSectors",
            "P_LoadSubsectors", "P_SetupLevel", "vertexes", "linedefs"
        };
    }
}
