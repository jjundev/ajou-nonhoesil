논리회로실험(ECE253) · 실험1 Basic Gates · 작성일 2026.08.29
## 1. 실험 목적
강의노트 p.2 는 이번 실험의 목적을 두 가지로 밝히고 있다. 첫째는 논리 게이트(logic gate)의 이해이고, 둘째는 논리 회로 구성 법칙의 이해로, 여기에는 부울대수(Boolean equation)와 드모르간(De Morgan) 법칙이 포함된다.
이번 주에 하는 세 가지 실험은 이 목적을 각각 다음과 같이 다룬다.
- 2입력 게이트 IC(74HC08, 74HC32, 74HC00, 74HC02)를 두 단으로 이어 붙여 3입력 AND·OR·NAND·NOR 게이트를 만들고, LED 로 읽은 출력을 진리표와 맞춰 본다.
- 인버터(74HC04)와 AND(74HC08), OR(74HC32)를 섞은 복합 논리회로를 꾸며, 여러 게이트가 만들어내는 부울식을 실제 회로에서 확인하고 드모르간 정리가 회로 수준에서 어떻게 나타나는지 본다.
## 2. 실험 이론
### 2.1 논리 레벨 — H/L 과 0/1
강의노트 p.3 은 논리값을 두 단계로 정의한다. L(Low)은 논리값 0 이고 전압으로는 0V, H(High)는 논리값 1 이고 전압으로는 3\~5V 다.
§2.2 의 2입력 이론표는 강의노트를 따라 H/L 로 적었고, §4 의 3입력 진리표는 실험실에서 LED 점등 여부로 읽을 것이므로 0/1 로 적었다. 같은 논리값을 가리키는 다른 표기일 뿐이지만, 강의노트와 대조할 때 헷갈리지 않도록 두 표기를 섞어 쓰지 않았다.
### 2.2 기본 게이트 — 2입력 이론표
강의노트 p.4\~p.8 은 AND·OR·NOT·NAND·NOR 각각의 기호와 부울식, 2입력 진리표를 차례로 보여 준다. 아래 네 표는 그 내용을 옮긴 것으로, 실험실에서 채우는 표가 아니라 3입력으로 확장하기 전의 기준이 되는 표다. 강의노트 표기를 그대로 두어 H/L 로 적었다.
**AND** (`A·B = C`, 강의노트 p.4) — 두 입력이 모두 H 일 때만 출력이 H 다.
<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>C</td>
</tr>
<tr>
<td>L</td>
<td>L</td>
<td>L</td>
</tr>
<tr>
<td>L</td>
<td>H</td>
<td>L</td>
</tr>
<tr>
<td>H</td>
<td>L</td>
<td>L</td>
</tr>
<tr>
<td>H</td>
<td>H</td>
<td>H</td>
</tr>
</table>
**OR** (`A+B = C`, 강의노트 p.5) — 두 입력 중 하나라도 H 이면 출력이 H 다.
<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>C</td>
</tr>
<tr>
<td>L</td>
<td>L</td>
<td>L</td>
</tr>
<tr>
<td>L</td>
<td>H</td>
<td>H</td>
</tr>
<tr>
<td>H</td>
<td>L</td>
<td>H</td>
</tr>
<tr>
<td>H</td>
<td>H</td>
<td>H</td>
</tr>
</table>
**NAND** (`(A·B)' = C`, 강의노트 p.7) — AND 출력을 뒤집은 것이다.
<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>C</td>
</tr>
<tr>
<td>L</td>
<td>L</td>
<td>H</td>
</tr>
<tr>
<td>L</td>
<td>H</td>
<td>H</td>
</tr>
<tr>
<td>H</td>
<td>L</td>
<td>H</td>
</tr>
<tr>
<td>H</td>
<td>H</td>
<td>L</td>
</tr>
</table>
**NOR** (`(A+B)' = C`, 강의노트 p.8) — OR 출력을 뒤집은 것이다.
<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>C</td>
</tr>
<tr>
<td>L</td>
<td>L</td>
<td>H</td>
</tr>
<tr>
<td>L</td>
<td>H</td>
<td>L</td>
</tr>
<tr>
<td>H</td>
<td>L</td>
<td>L</td>
</tr>
<tr>
<td>H</td>
<td>H</td>
<td>L</td>
</tr>
</table>
> 출처: 강의노트 p.4·p.5·p.7·p.8 의 진리표.
강의노트 p.9 에는 XOR(`A⊕B = (A'·B)+(A·B')`)도 나오고 준비물에도 74HC86 이 들어 있지만, p.11\~p.13 의 실험 회로 어디에도 XOR 를 쓰는 항목이 없다. 그래서 XOR 는 이론으로만 짚고 넘어간다.
### 2.3 2입력 게이트로 3입력 만들기
이번 실험의 앞 두 항목은 2입력 IC 만으로 3입력 게이트를 만드는 것이다. AND 와 OR 는 결합법칙이 성립하므로 두 단으로 나눌 수 있다.
- `A·B·C = (A·B)·C` — 첫 게이트가 `A·B` 를 만들고, 둘째 게이트가 그 결과와 `C` 를 다시 AND 한다.
- `A+B+C = (A+B)+C` — OR 도 같은 방식이다.
그런데 NAND 와 NOR 는 결합법칙이 성립하지 않는다. `(A↑B)↑C` 와 `A↑(B↑C)` 는 서로 다르다. 그래서 강의노트 p.12 의 3입력 NAND 는 NAND 를 두 단 쌓는 대신, AND 로 `A·B` 를 먼저 만든 뒤 NAND 로 `C` 와 합치는 구조를 쓴다. 식으로 쓰면 `(A·B·C)' = (A·B)↑C` 다. NOR 도 같은 이유로 OR 다음에 NOR 를 붙인다.
이 점을 놓치고 NAND 두 개를 이어 붙이면 진리표가 전혀 다르게 나온다.
### 2.4 드모르간 정리와 복합회로
드모르간 정리는 `(A·B)' = A' + B'` 와 `(A+B)' = A'·B'` 이며, 강의노트 p.2 가 이번 실험의 학습 목표로 명시한 내용이다.
강의노트 p.13 복합회로의 세 출력을 부울대수로 정리하면 이렇게 된다.
- `Z = (A'·B)'` 이고, 드모르간을 적용하면 `Z = A + B'` 다.
- `X = A + Z = A + (A + B') = A + B'` 다. 멱등법칙 `A + A = A` 를 썼다.
- `Y = A + B` 다.
즉 `X` 와 `Z` 는 대수적으로 같은 식이 된다. 회로에서 X 쪽 LED 와 Z 쪽 LED 가 서로 다르게 켜진다면 그것만으로 배선이 잘못됐다는 뜻이므로, 계측기 없이도 스스로 검산할 수 있는 셈이다.
## 3. 실험 부품
### 3.1 준비물
강의노트 p.10 의 준비물은 다음과 같다.
<table header-row="true">
<tr>
<td>항목</td>
<td>수량</td>
<td>비고</td>
</tr>
<tr>
<td>5V 전압원</td>
<td>1</td>
<td>모든 IC 의 14번 핀</td>
</tr>
<tr>
<td>74HC00 (quad 2-input NAND)</td>
<td>1개</td>
<td>3입력 NAND</td>
</tr>
<tr>
<td>74HC02 (quad 2-input NOR)</td>
<td>1개</td>
<td>3입력 NOR</td>
</tr>
<tr>
<td>74HC04 (hex inverter)</td>
<td>2개</td>
<td>복합회로</td>
</tr>
<tr>
<td>74HC08 (quad 2-input AND)</td>
<td>1개</td>
<td>세 항목 모두</td>
</tr>
<tr>
<td>74HC32 (quad 2-input OR)</td>
<td>1개</td>
<td>세 항목 모두</td>
</tr>
<tr>
<td>74HC86 (quad 2-input XOR)</td>
<td>1개</td>
<td>이번 실험 항목에는 쓰지 않는다</td>
</tr>
<tr>
<td>발광다이오드</td>
<td>3개</td>
<td>330Ω 직렬 필수</td>
</tr>
</table>
74HC08 과 74HC32 는 한 개씩뿐이라 세 항목의 회로를 브레드보드에 동시에 올릴 수 없다. 항목이 바뀔 때마다 같은 칩을 다시 배선해서 쓰게 된다. LED 가 3개인 것은 복합회로의 출력이 X·Y·Z 세 개이기 때문으로 보인다.
### 3.2 핀 배치 (DIP-14)
<table header-row="true">
<tr>
<td>IC</td>
<td>게이트1</td>
<td>게이트2</td>
<td>게이트3</td>
<td>게이트4</td>
<td>VCC</td>
<td>GND</td>
</tr>
<tr>
<td>74HC00 (quad NAND)</td>
<td>1,2 → 3</td>
<td>4,5 → 6</td>
<td>9,10 → 8</td>
<td>12,13 → 11</td>
<td>14</td>
<td>7</td>
</tr>
<tr>
<td>74HC08 (quad AND)</td>
<td>1,2 → 3</td>
<td>4,5 → 6</td>
<td>9,10 → 8</td>
<td>12,13 → 11</td>
<td>14</td>
<td>7</td>
</tr>
<tr>
<td>74HC32 (quad OR)</td>
<td>1,2 → 3</td>
<td>4,5 → 6</td>
<td>9,10 → 8</td>
<td>12,13 → 11</td>
<td>14</td>
<td>7</td>
</tr>
<tr>
<td>**74HC02 (quad NOR)**</td>
<td>**2,3 → 1**</td>
<td>**5,6 → 4**</td>
<td>**8,9 → 10**</td>
<td>**11,12 → 13**</td>
<td>14</td>
<td>7</td>
</tr>
</table>
74HC04(hex inverter)는 1→2, 3→4, 5→6, 9→8, 11→10, 13→12 이고 VCC 는 14번, GND 는 7번이다.
위 배치는 74HC 계열 DIP-14 의 표준 배치를 따른 것이므로, 실험 전에 실물 칩의 각인을 보고 한 번 대조하는 편이 안전하다.
특히 **74HC02 는 나머지 셋과 핀 배치가 다르다.** 74HC00·74HC08·74HC32 는 3·6·8·11번이 출력이지만, 74HC02 는 1·4·10·13번이 출력이다. 나머지 칩과 똑같이 생겼기 때문에 이번 실험에서 가장 실수하기 쉬운 부분이다.
### 3.3 LED 와 전류 제한 저항
강의노트 p.11·p.12·p.13 에는 모두 "다이오드 연결 시, 330Ω 저항 필수" 라는 문구가 붙어 있다. LED 는 애노드 쪽에 330Ω 을 직렬로 넣고 캐소드를 GND 로 내린다.
74HC 출력을 약 4.5V, LED 순방향 전압을 약 2V 로 잡으면 330Ω 에 흐르는 전류는 대략 (4.5 − 2) / 330 ≈ 7.6mA 가 된다. 74HC 계열의 권장 출력 전류보다 다소 큰 값이므로, 강의노트 지시대로 330Ω 을 쓰되 LED 가 생각보다 어둡다면 이 점을 먼저 의심해 볼 만하다.
### 3.4 미사용 핀 처리
미사용 입력핀은 전부 GND 로 내린다. 띄워 두면 CMOS 입력이 주변 잡음을 주워 출력이 흔들리는데, 이 실험에서 결과가 안 맞는 가장 흔한 원인이다.
반대로 미사용 출력핀은 아무 데도 연결하지 않고 그대로 둔다. 출력끼리 묶거나 GND 로 내리면 칩이 상한다.
입력 A·B·C 도 점퍼선으로 +5V 또는 GND 에 직접 물린다. 스위치가 없다고 해서 띄워 두면 안 된다.
## 4. 실험 과정 및 예상 결과
### 4.1 3입력 AND / OR 게이트 구성
강의노트 p.11 의 회로다. 2입력 게이트 두 개를 이어 붙여 3입력을 만든다. 회로도에는 LED 가 두 개 달려 있는데, 첫 게이트의 출력(`A·B`)에 하나, 둘째 게이트의 최종 출력(`A·B·C`)에 하나가 붙는다. 진리표로 확인할 대상은 최종 출력 쪽이고, 앞쪽 LED 는 중간 단이 제대로 동작하는지 눈으로 보기 위한 것이다.
OR 회로는 같은 구조에서 IC 만 74HC32 로 바꿔 반복한다. 강의노트가 IC 를 지정하지 않고 "OR gate에 대한 IC 찾아서 수행" 이라고만 적어 두었으므로, 준비물 중 2입력 OR 인 74HC32 를 골랐다.
**진행 순서.** §5.2 대로 배선한 뒤, 입력 A·B·C 를 000 부터 111 까지 여덟 가지 조합으로 차례대로 넣고, 각 조합에서 최종 출력 LED 가 켜지는지 기록해 아래 예상표와 비교한다.
**3입력 AND 예상 진리표**
<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>C</td>
<td>Y</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
</table>
> 출처: `Y = A·B·C` 로 직접 계산했다. 입력 세 개의 모든 조합이므로 8행이다.
**3입력 OR 예상 진리표**
<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>C</td>
<td>Y</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
</table>
> 출처: `Y = A+B+C` 로 직접 계산했다.
### 4.2 3입력 NAND / NOR 게이트 구성
강의노트 p.12 의 회로다. §2.3 에서 정리한 대로 NAND 는 결합법칙이 성립하지 않으므로 NAND 두 단이 아니라 74HC08 과 74HC00 을 조합한다. 앞 게이트인 74HC08 이 `A·B` 를 만들고, 뒤의 74HC00 이 그 결과와 `C` 를 받아 `(A·B·C)'` 를 낸다. 앞 항목과 마찬가지로 중간 단과 최종 단에 LED 가 하나씩 붙는다.
NOR 회로는 같은 구조에서 74HC32 와 74HC02 를 쓴다. 이때 74HC02 의 핀 배치가 다르다는 점(§3.2)을 특히 조심해야 한다.
**진행 순서.** 앞 항목과 같다. 여덟 가지 입력 조합을 차례로 넣고 최종 출력을 기록한다.
**3입력 NAND 예상 진리표**
<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>C</td>
<td>Y</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
</table>
> 출처: `Y = (A·B·C)'` 로 직접 계산했다. 3입력 AND 의 출력을 전부 뒤집은 것과 같다.
**3입력 NOR 예상 진리표**
<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>C</td>
<td>Y</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
</table>
> 출처: `Y = (A+B+C)'` 로 직접 계산했다. 3입력 OR 의 출력을 전부 뒤집은 것과 같다.
### 4.3 복합 논리회로 구성
강의노트 p.13 의 회로다. 입력은 A 와 B 두 개뿐이고 출력이 X·Y·Z 세 개다. 회로도에 C 입력은 없다. LED 가 세 개인 것도 이 출력 개수와 맞는다.
**진행 순서.** §5.4 대로 배선한 뒤 입력 A·B 를 00, 01, 10, 11 네 조합으로 넣고 세 LED 의 점등을 함께 기록한다. 이때 X 쪽과 Z 쪽 LED 가 항상 같이 켜지는지 확인한다. §2.4 에서 본 대로 두 출력은 대수적으로 같은 식이므로, 다르게 켜진다면 배선이 잘못된 것이다.
**복합회로 예상 진리표**
<table header-row="true">
<tr>
<td>A</td>
<td>B</td>
<td>X</td>
<td>Y</td>
<td>Z</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
</table>
> 출처: 강의노트 p.13 회로도에서 읽은 배선을 부울식으로 옮겨 계산했다. `X = A + (A'·B)'`, `Y = A + B`, `Z = (A'·B)'` 다. §2.4 에서 정리했듯 X 와 Z 는 같은 식이며, 위 표에서도 두 열의 값이 일치한다.
## 5. 회로 결선도
### 5.1 공통 규칙
모든 IC 는 14번 핀을 +5V 에, 7번 핀을 GND 에 연결한다. 미사용 입력핀은 전부 GND 로 내리고, 미사용 출력핀은 그대로 둔다. 입력 A·B·C 는 점퍼선으로 +5V 또는 GND 에 직접 물린다. LED 는 애노드 쪽에 330Ω 을 직렬로 넣고 캐소드를 GND 로 보낸다.
아래 표에서 U1·U3·U8 은 모두 같은 74HC08 한 개를 가리키고, U2·U5·U9 도 같은 74HC32 한 개다. 항목마다 다시 배선해서 쓴다는 뜻이다.
### 5.2 3입력 AND / OR 배선
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
</tr>
<tr>
<td>U1 = 74HC08</td>
<td>14 / 7</td>
<td>+5V / GND</td>
</tr>
<tr>
<td></td>
<td>1 / 2</td>
<td>입력 A / 입력 B</td>
</tr>
<tr>
<td></td>
<td>3</td>
<td>U1 의 4번 핀으로, 그리고 첫 LED 애노드(330Ω) → GND</td>
</tr>
<tr>
<td></td>
<td>5</td>
<td>입력 C</td>
</tr>
<tr>
<td></td>
<td>6</td>
<td>최종 LED 애노드(330Ω) → GND. 출력 `Y = A·B·C`</td>
</tr>
<tr>
<td></td>
<td>9, 10, 12, 13</td>
<td>GND (미사용 입력)</td>
</tr>
<tr>
<td></td>
<td>8, 11</td>
<td>개방 (미사용 출력)</td>
</tr>
</table>
OR 회로는 U1 을 74HC32 로 바꾸기만 하고 나머지 배선은 같다. 최종 출력은 `Y = A+B+C` 가 된다.
### 5.3 3입력 NAND / NOR 배선
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
</tr>
<tr>
<td>U3 = 74HC08</td>
<td>14 / 7</td>
<td>+5V / GND</td>
</tr>
<tr>
<td></td>
<td>1 / 2</td>
<td>입력 A / 입력 B</td>
</tr>
<tr>
<td></td>
<td>3</td>
<td>U4 의 1번 핀으로(`A·B`), 그리고 첫 LED 애노드(330Ω) → GND</td>
</tr>
<tr>
<td></td>
<td>4, 5, 9, 10, 12, 13</td>
<td>GND</td>
</tr>
<tr>
<td></td>
<td>6, 8, 11</td>
<td>개방</td>
</tr>
<tr>
<td>U4 = 74HC00</td>
<td>14 / 7</td>
<td>+5V / GND</td>
</tr>
<tr>
<td></td>
<td>1 / 2</td>
<td>U3 의 3번 핀 / 입력 C</td>
</tr>
<tr>
<td></td>
<td>3</td>
<td>최종 LED 애노드(330Ω) → GND. 출력 `Y = (A·B·C)'`</td>
</tr>
<tr>
<td></td>
<td>4, 5, 9, 10, 12, 13</td>
<td>GND</td>
</tr>
<tr>
<td></td>
<td>6, 8, 11</td>
<td>개방</td>
</tr>
</table>
NOR 회로는 U3 자리에 74HC32 를, U4 자리에 74HC02 를 놓는다. 74HC02 는 핀이 다르므로 따로 적는다.
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
</tr>
<tr>
<td>U6 = 74HC02</td>
<td>14 / 7</td>
<td>+5V / GND</td>
</tr>
<tr>
<td></td>
<td>2</td>
<td>앞 단 74HC32 의 3번 핀 (1번 핀이 아니다)</td>
</tr>
<tr>
<td></td>
<td>3</td>
<td>입력 C</td>
</tr>
<tr>
<td></td>
<td>1</td>
<td>최종 LED 애노드(330Ω) → GND. 이 핀이 출력이다. `Y = (A+B+C)'`</td>
</tr>
<tr>
<td></td>
<td>5, 6, 8, 9, 11, 12</td>
<td>GND</td>
</tr>
<tr>
<td></td>
<td>4, 10, 13</td>
<td>개방</td>
</tr>
</table>
### 5.4 복합 논리회로 배선
<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
</tr>
<tr>
<td>U7 = 74HC04</td>
<td>14 / 7</td>
<td>+5V / GND</td>
</tr>
<tr>
<td></td>
<td>1 → 2</td>
<td>입력 A 를 받아 `A'` 를 U8 의 1번 핀으로</td>
</tr>
<tr>
<td></td>
<td>3 → 4</td>
<td>U8 의 3번 핀을 받아 `Z = (A'·B)'` 를 U9 의 2번 핀으로, 그리고 Z 쪽 LED 애노드(330Ω) → GND</td>
</tr>
<tr>
<td></td>
<td>5, 9, 11, 13</td>
<td>GND</td>
</tr>
<tr>
<td></td>
<td>6, 8, 10, 12</td>
<td>개방</td>
</tr>
<tr>
<td>U8 = 74HC08</td>
<td>14 / 7</td>
<td>+5V / GND</td>
</tr>
<tr>
<td></td>
<td>1 / 2</td>
<td>U7 의 2번 핀(`A'`) / 입력 B</td>
</tr>
<tr>
<td></td>
<td>3</td>
<td>U7 의 3번 핀으로 (`A'·B`)</td>
</tr>
<tr>
<td></td>
<td>4, 5, 9, 10, 12, 13</td>
<td>GND</td>
</tr>
<tr>
<td></td>
<td>6, 8, 11</td>
<td>개방</td>
</tr>
<tr>
<td>U9 = 74HC32</td>
<td>14 / 7</td>
<td>+5V / GND</td>
</tr>
<tr>
<td></td>
<td>1 / 2</td>
<td>입력 A / U7 의 4번 핀(`Z`)</td>
</tr>
<tr>
<td></td>
<td>3</td>
<td>X 쪽 LED 애노드(330Ω) → GND. `X = A + Z`</td>
</tr>
<tr>
<td></td>
<td>4 / 5</td>
<td>입력 A / 입력 B</td>
</tr>
<tr>
<td></td>
<td>6</td>
<td>Y 쪽 LED 애노드(330Ω) → GND. `Y = A + B`</td>
</tr>
<tr>
<td></td>
<td>9, 10, 12, 13</td>
<td>GND</td>
</tr>
<tr>
<td></td>
<td>8, 11</td>
<td>개방</td>
</tr>
</table>
`Z` 노드는 LED 와 U9 의 2번 핀 양쪽으로 갈라진다. 앞서 본 대로 `X` 와 `Z` 는 같은 식이므로 두 LED 는 언제나 함께 켜져야 한다.
### 5.5 실험 전 확인할 사항
- 74HC 계열 IC 의 핀 배치는 표준 배치를 따랐다. 실물 칩의 각인을 보고 한 번 대조한다. 특히 74HC02 는 다른 칩과 출력 핀이 다르다.
- 강의노트가 입력용 스위치를 따로 지정하지 않아 점퍼선을 직접 꽂는 것으로 가정했다. 실험실 키트에 딥스위치가 있으면 그쪽이 편하다.
- 330Ω 에서 LED 전류가 약 7.6mA 로 74HC 권장 구동 전류를 조금 넘는다. 강의노트 지시대로 따르되 LED 가 어두우면 이 점을 먼저 본다.
### 5.6 브레드보드 작도
아래는 배선 전의 빈 브레드보드다. §5.2\~§5.4 의 표를 보면서 신호명과 전원, 저항값을 손으로 적어 가며 배선을 그린다. 핀 번호만 늘어놓기보다 어느 선이 무슨 신호인지 적어 두는 편이 실험실에서 훨씬 빨리 찾을 수 있다.
![브레드보드 작도 캔버스]()
## 6. 출처 및 참고문헌
1. 논리회로실험 강의노트 "실험1 Basic Gates" — p.2 실험 목적, p.3 논리 레벨 정의, p.4\~p.9 게이트별 기호·부울식·진리표, p.10 실험 준비물, p.11\~p.13 실험 회로도.