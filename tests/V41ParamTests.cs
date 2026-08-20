// ============================================================================
// V41ParamTests.cs - every [Range] must actually contain its own default.
//
// This exists because of a real defect. ThesisClusterMinutes was declared
// [Range(1, 20)] and defaulted to 60 - the Range was copy-pasted from the
// bar-count parameters sitting above it instead of the minutes ones. The
// package compiled cleanly, every behavioural test passed, and NinjaTrader
// then refused to load the strategy at all:
//
//   Value of property 'ThesisClusterMinutes' of NinjaScript
//   'MnqV41StructureResearch' is 60 and not in valid range between 1 and 20.
//
// A compiler cannot catch that, and no unit test of the ENGINES can either,
// because the mistake lives entirely in the host's attribute metadata. So
// this walks the actual attributes by reflection, runs SetDefaults exactly
// as NinjaTrader does, and asserts that every default sits inside its own
// declared range.
//
// It catches the whole class of error, not just the one instance found.
// ============================================================================

using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.Reflection;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies;

namespace MnqTwoTests
{
    public static class V41ParamTests
    {
        private static int passed, failed;
        private static void Check(bool c, string name)
        {
            if (c) { passed++; Console.WriteLine("  PASS  " + name); }
            else { failed++; Console.WriteLine("  FAIL  " + name); }
        }

        public static int Run()
        {
            passed = failed = 0;
            Console.WriteLine("V4.1 PARAMETER RANGE TESTS");

            Validate(new MnqV41StructureResearch(), "MnqV41StructureResearch");
            Validate(new MnqV41OrderFlowResearch(), "MnqV41OrderFlowResearch");

            Console.WriteLine("V4.1 params: " + passed + " passed, " + failed + " failed");
            return failed;
        }

        /// Drive SetDefaults the way NinjaTrader does, then check every
        /// [Range]-decorated property against its own attribute.
        private static void Validate(object strategy, string label)
        {
            Console.WriteLine(" " + label);
            Type t = strategy.GetType();

            // NinjaTrader sets State then calls the protected OnStateChange.
            FieldInfo stateField = FindField(t, "State");
            if (stateField == null) { Check(false, label + ": State field not reachable"); return; }
            stateField.SetValue(strategy, State.SetDefaults);

            MethodInfo onState = FindMethod(t, "OnStateChange");
            if (onState == null) { Check(false, label + ": OnStateChange not reachable"); return; }
            onState.Invoke(strategy, null);

            int checkedCount = 0;
            PropertyInfo[] props = t.GetProperties(BindingFlags.Public | BindingFlags.Instance);
            for (int i = 0; i < props.Length; i++)
            {
                PropertyInfo p = props[i];
                object[] ranges = p.GetCustomAttributes(typeof(RangeAttribute), true);
                if (ranges.Length == 0) continue;
                RangeAttribute r = (RangeAttribute)ranges[0];

                object v;
                try { v = p.GetValue(strategy, null); }
                catch (Exception) { continue; }
                if (v == null) continue;

                double val = Convert.ToDouble(v, CultureInfo.InvariantCulture);
                double lo = Convert.ToDouble(r.Minimum, CultureInfo.InvariantCulture);
                double hi = Convert.ToDouble(r.Maximum, CultureInfo.InvariantCulture);

                checkedCount++;
                Check(val >= lo && val <= hi,
                      p.Name + " default " + val.ToString("0.####", CultureInfo.InvariantCulture)
                      + " is inside [" + lo.ToString("0.####", CultureInfo.InvariantCulture)
                      + ", " + hi.ToString("0.####", CultureInfo.InvariantCulture) + "]");

                // A range that cannot hold its own default is the defect above;
                // an inverted range is the same mistake wearing a hat.
                Check(lo <= hi, p.Name + " range is not inverted");
            }

            Check(checkedCount > 0, label + ": found [Range] attributes to check");
        }

        private static FieldInfo FindField(Type t, string name)
        {
            while (t != null)
            {
                FieldInfo f = t.GetField(name,
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
                if (f != null) return f;
                t = t.BaseType;
            }
            return null;
        }

        private static MethodInfo FindMethod(Type t, string name)
        {
            while (t != null)
            {
                MethodInfo m = t.GetMethod(name,
                    BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance,
                    null, Type.EmptyTypes, null);
                if (m != null) return m;
                t = t.BaseType;
            }
            return null;
        }
    }
}
