package cmd

import (
	"encoding/json"
	"fmt"
	"os"

	"sdd-compile/internal/govcompiler"

	"github.com/spf13/cobra"
)

var compileCmd = &cobra.Command{
	Use:   "compile",
	Short: "Compile governance JSON to msgpack artifacts",
	Long:  "Compile governance-core.json and governance-client.json to msgpack format. Outputs JSON result to stdout.",
	RunE: func(cmd *cobra.Command, args []string) error {
		input, _ := cmd.Flags().GetString("input")
		output, _ := cmd.Flags().GetString("output")

		if input == "" {
			input = ".providence/compiled"
		}
		if output == "" {
			output = ".providence/compiled"
		}

		result, err := govcompiler.New(input).Compile(output)
		if err != nil {
			fmt.Fprintf(os.Stderr, "compile error: %v\n", err)
			// Emit failure JSON to stdout for Python bridge to parse
			out := map[string]any{"ok": false, "error": err.Error()}
			json.NewEncoder(os.Stdout).Encode(out)
			os.Exit(1)
		}

		out := map[string]any{
			"ok":                  true,
			"core_msgpack_file":   result.CoreMsgpackFile,
			"client_msgpack_file": result.ClientMsgpackFile,
			"core_metadata":       result.CoreMetadata,
			"client_metadata":     result.ClientMetadata,
			"core_fingerprint":    result.CoreFingerprint,
			"client_fingerprint":  result.ClientFingerprint,
			"core_fingerprint_salt": result.CoreFingerprintSalt,
			"core_item_count":     result.CoreItemCount,
			"client_item_count":   result.ClientItemCount,
			"signed":              result.Signed,
			"signer_key_id":       result.SignerKeyID,
			"signature_files":     result.SignatureFiles,
		}
		return json.NewEncoder(os.Stdout).Encode(out)
	},
}

func init() {
	rootCmd.AddCommand(compileCmd)
	compileCmd.Flags().StringP("input", "i", "", "Directory containing governance JSON files (default: .providence/compiled)")
	compileCmd.Flags().StringP("output", "o", "", "Directory to write compiled artifacts (default: .providence/compiled)")
}
