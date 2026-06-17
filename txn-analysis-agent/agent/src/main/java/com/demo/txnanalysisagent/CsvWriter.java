package com.demo.txnanalysisagent;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;

/**
 * Appends evaluation results to a CSV file.
 * Creates the file with a header row if it doesn't exist.
 */
public class CsvWriter {

    private static final Logger log = LoggerFactory.getLogger(CsvWriter.class);
    private static final String HEADER = "transaction_id,input_log,output_response,model_id,latency,input_tokens,output_tokens,total_cost";

    private final Path csvPath;

    public CsvWriter(Path csvPath) {
        this.csvPath = csvPath;
    }

    /**
     * Appends a result row to the CSV file.
     */
    public void append(String transactionId, String inputLog, String outputResponse,
                       String modelId, long latencyMs, int inputTokens, int outputTokens,
                       double totalCost) {
        try {
            if (!Files.exists(csvPath)) {
                Files.writeString(csvPath, HEADER + "\n", StandardCharsets.UTF_8,
                        StandardOpenOption.CREATE, StandardOpenOption.WRITE);
                log.info("Created CSV file with header: {}", csvPath);
            }

            String row = "%s,%s,%s,%s,%d,%d,%d,%.6f".formatted(
                    escapeCsv(transactionId),
                    escapeCsv(inputLog),
                    escapeCsv(outputResponse),
                    escapeCsv(modelId),
                    latencyMs,
                    inputTokens,
                    outputTokens,
                    totalCost
            );

            Files.writeString(csvPath, row + "\n", StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);

            log.info("Result appended to CSV for transaction: {} (cost: ${})", transactionId, String.format("%.6f", totalCost));
        } catch (IOException e) {
            log.error("Failed to write to CSV file: {}", csvPath, e);
            throw new RuntimeException("Failed to write CSV", e);
        }
    }

    /**
     * Escapes a value for CSV: wraps in double quotes and escapes internal quotes.
     */
    private static String escapeCsv(String value) {
        if (value == null) {
            return "\"\"";
        }
        return "\"" + value.replace("\"", "\"\"") + "\"";
    }
}
