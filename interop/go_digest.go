package main
import("crypto/sha256";"encoding/hex";"encoding/json";"fmt";"os";"path/filepath")
type Vector struct{Name string `json:"name"`; Value any `json:"value"`}
func rejectFloats(v any) error { switch x:=v.(type){case map[string]any: for _,y:=range x{if e:=rejectFloats(y);e!=nil{return e}}; case []any:for _,y:=range x{if e:=rejectFloats(y);e!=nil{return e}}; case float64: if x!=float64(int64(x)){return fmt.Errorf("float forbidden")}; if x < -9007199254740991 || x > 9007199254740991 {return fmt.Errorf("JSON parser precision risk")}}; return nil }
func main(){
  exe,_:=os.Getwd(); p:=filepath.Join(exe,"test_vectors","canonicalization_vectors.json"); if _,e:=os.Stat(p);e!=nil{p=filepath.Join("..","test_vectors","canonicalization_vectors.json")}
  b,e:=os.ReadFile(p);if e!=nil{panic(e)}; var vs []Vector; if e=json.Unmarshal(b,&vs);e!=nil{panic(e)}
  for _,v:=range vs{if e:=rejectFloats(v.Value);e!=nil{panic(e)}; c,e:=json.Marshal(v.Value);if e!=nil{panic(e)}; h:=sha256.Sum256(c);fmt.Println(v.Name,hex.EncodeToString(h[:]))}
}
