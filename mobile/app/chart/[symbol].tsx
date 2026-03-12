import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';

export default function ChartScreen() {
  const { symbol } = useLocalSearchParams();

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
          <Text style={styles.backTxt}>← Back</Text>
        </TouchableOpacity>
        <View style={{ flex: 1, alignItems: 'center' }}>
          <Text style={styles.title}>{symbol}</Text>
        </View>
        <View style={{ width: 60 }} />
      </View>
      <View style={styles.chartArea}>
        <Text style={{ fontSize: 40, marginBottom: 16 }}>📈</Text>
        <Text style={styles.txt}>Interactive Chart Region</Text>
        <Text style={{ color: '#00D4FF', marginTop: 12 }}>{symbol} • NSE</Text>
      </View>
    </SafeAreaView>
  );
}
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#070B14' },
  header: { flexDirection: 'row', alignItems: 'center', padding: 16, borderBottomWidth: 1, borderBottomColor: '#1A2332' },
  backBtn: { width: 60 },
  backTxt: { color: '#8899AA', fontSize: 15 },
  title: { fontSize: 18, fontWeight: '700', color: '#FFF' },
  chartArea: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  txt: { color: '#8899AA', fontSize: 16 },
});
