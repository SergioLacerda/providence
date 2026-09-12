package cmd

import (
	"encoding/json"
	"fmt"
	"os"

	"sdd-compile/internal/govcompiler"

	"github.com/spf13/cobra"
)

var validateCmd = &cobra.Command{
	Use:   "validate",
	Short: "Validate compiled governance artifacts",
	Long:  "Validate compiled artifacts for schema compliance and fingerprint integrity. Outputs JSON result to stdout.",
	RunE: func(cmd *cobra.Command, args []string) error {
		dir, _ := cmd.Flags().GetString("dir")
		if dir == "" {
			dir = ".providence/compiled"
		}

		vr := govcompiler.New(dir).ValidateCompilationDetailed(dir)

		checks := make([]map[string]any, len(vr.Checks))
		for i, c := range vr.Checks {
			checks[i] = map[string]any{"name": c.Name, "ok": c.OK, "details": c.Details}
		}

		out := map[string]any{
			"ok":     vr.OK,
			"errors": vr.Errors,
			"checks": checks,
		}
		if err := json.NewEncoder(os.Stdout).Encode(out); err != nil {
			return err
		}

		if !vr.OK {
			fmt.Fprintf(os.Stderr, "validation failed: %v\n", vr.Errors)
			os.Exit(1)
		}
		return nil
	},
}

func init() {
	rootCmd.AddCommand(validateCmd)
	validateCmd.Flags().StringP("dir", "d", "", "Directory containing compiled artifacts to validate (default: .providence/compiled)")
}
