<table_of_contents color="gray"/>
<empty-block/>
# 실험 목적
디코딩과 인코딩이라는 두 가지 코드 변환 동작을 회로로 직접 꾸며 보고 그 동작 원리를 이해한다. 강의노트가 밝힌 이번 실험의 목적이 그것이다.
디코더는 입력선에 실린 n비트 2진 코드를 최대 2ⁿ 개의 서로 다른 정보로 바꿔 주는 조합논리회로이고, 인코더는 그 반대 방향으로 활성화된 입력선 하나를 받아 그 번호에 해당하는 2진 코드를 만든다. 이번 실험은 이 두 방향을 각각 두 번씩 다룬다. 방향마다 먼저 게이트로 직접 꾸며 원리를 확인하고, 이어서 같은 방향의 변환을 한 칩에 담은 MSI 부품을 붙인다.
진행 순서는 네 단계다. 먼저 인버터와 AND 게이트만으로 2X4 디코더를 세워 디코더가 최소항 생성기라는 것을 확인하고, 이어서 74HC42 로 4비트 BCD 를 10진 열 줄로 푸는 MSI 디코더를 붙인다. 후반부는 방향이 뒤집힌다. 인버터와 4입력 NAND 로 10진 입력을 Excess-3 코드로 바꾸는 인코더를 만들고, 마지막으로 74HC148 우선순위 인코더에 입력을 여러 개 동시에 넣어 우선순위가 어떻게 결정되는지 본다.
<empty-block/>
<empty-block/>
# 실험 이론
## 디코더
디코더는 n개의 입력 변수로 만들 수 있는 최소항을 2ⁿ개 이하의 출력으로 바꿔 준다. 출력 하나하나가 입력 조합 하나에 대응하므로, 어떤 입력을 넣든 활성화되는 출력은 정확히 하나다. 강의노트는 3X8 디코더를 예로 들어 여덟 출력을 최소항 여덟 개로 적어 둔다.
- **3X8 디코더 이론표**
	<table header-row="true">
<tr>
<td>A2</td>
<td>A1</td>
<td>A0</td>
<td>D7</td>
<td>D6</td>
<td>D5</td>
<td>D4</td>
<td>D3</td>
<td>D2</td>
<td>D1</td>
<td>D0</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
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
<td>0</td>
<td>0</td>
<td>0</td>
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
<td>0</td>
<td>0</td>
<td>0</td>
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
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
여덟 출력의 부울식은 `D0 = A2'·A1'·A0'`, `D1 = A2'·A1'·A0`, `D2 = A2'·A1·A0'`, `D3 = A2'·A1·A0`, `D4 = A2·A1'·A0'`, `D5 = A2·A1'·A0`, `D6 = A2·A1·A0'`, `D7 = A2·A1·A0` 이다. 각 식이 입력 세 개와 그 보수를 골라 AND 로 묶은 최소항 하나라는 점이 디코더의 전부다. 이번 실험에서 만드는 2X4 디코더는 이 구조를 `n = 2` 로 줄인 것이어서, 입력 두 개와 그 보수를 AND 로 짝지으면 곧바로 네 개의 최소항이 나온다.
<empty-block/>
## 인코더
인코더는 디코더의 반대다. 2ⁿ개의 입력 중 활성화된 하나를 받아 그 번호에 해당하는 n비트 2진 코드를 출력한다. 출력 비트마다 "그 자리에 1 이 서는 입력 번호"를 모아 OR 로 묶으면 식이 완성된다.
- **8X3 인코더 이론표**
	<table header-row="true">
<tr>
<td>D7</td>
<td>D6</td>
<td>D5</td>
<td>D4</td>
<td>D3</td>
<td>D2</td>
<td>D1</td>
<td>D0</td>
<td>A2</td>
<td>A1</td>
<td>A0</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
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
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
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
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
부울식은 `A0 = D1+D3+D5+D7`, `A1 = D2+D3+D6+D7`, `A2 = D4+D5+D6+D7` 이다. 강의노트는 이 표 옆에 임의의 순간 오직 하나의 입력만 1 이어야 한다고 못을 박아 두었다. 표에 여덟 행뿐인 것도 그 때문이고, 이 제약이 단순 인코더의 약점이기도 하다. 입력 두 개가 동시에 들어오면 출력은 두 코드를 OR 한 값이 되어 어느 쪽도 가리키지 않는 엉뚱한 코드가 나온다.
<empty-block/>
## 우선순위 인코더
우선순위 인코더는 위의 약점을 회로 안에서 해결한 부품이다. 입력이 여러 개 동시에 활성이어도 그중 가중치가 가장 높은 하나만 인코딩하고 나머지는 무시한다. 그래서 진리표에 don't care 가 등장한다. 우선순위가 높은 입력이 이미 잡혔다면 그 아래 입력이 무엇이든 출력이 바뀌지 않기 때문이다.
74HC148 은 여기에 제어 핀 세 개를 더 얹는다. `EI` (Active Low) 는 칩을 동작시키는 인에이블이어서 0 이어야 나머지 핀이 의미를 갖는다. `GS` (Active Low) 는 칩이 켜져 있고 활성 입력이 하나라도 있을 때 0 이 되는 유효 데이터 표시이고, `EO` (Active Low) 는 칩이 켜져 있는데 활성 입력이 하나도 없을 때 0 이 된다. 이 두 신호가 필요한 이유는 코드 출력만으로는 "아무 입력도 없음"과 "0번 입력이 활성"을 구별할 수 없기 때문이다. 두 경우 모두 코드 출력이 같은 값으로 나오는데, `EI` 가 0 인 동안 `GS` 와 `EO` 는 서로의 보수여서 두 신호가 함께 갈라 준다. `EO` 를 따로 둔 이유는 여기에 더해 칩을 여러 개 이어 붙일 때에 있다 — 앞 칩의 `EO` 를 뒤 칩의 `EI` 로 넣으면 "내 쪽에는 활성 입력이 없으니 네가 받아라"가 전달되어 입력 수를 늘릴 수 있다.
<empty-block/>
## Excess-3 코드
Excess-3 는 BCD 코드에 3(`0011`)을 더해 만드는 코드다. 십진 0 은 BCD `0000` 에 `0011` 을 더한 `0011` 이고, 십진 5 는 `0101` 에 더해 `1000` 이 된다. 강의노트는 각 비트를 반전하면 9의 보수를 얻을 수 있어 자기보수 코드라고도 부른다고 적는다. 실제로 십진 0 의 `0011` 을 뒤집으면 `1100` 인데 이것이 십진 9 의 Excess-3 코드다.
<empty-block/>
## 인버터와 NAND 로 만드는 OR
Excess-3 인코더는 출력 비트마다 "그 비트가 1 인 십진수들의 OR" 를 만들어야 하는데, 이번 주 준비물에는 OR 게이트가 없다. 대신 인버터와 4입력 NAND 를 두 단으로 잇는다. 드모르간 법칙에 따라 `(A'·B'·C'·D')' = A+B+C+D` 이므로, 인버터가 먼저 각 입력을 반전해 두면 NAND 한 단이 그대로 OR 가 된다.
이 구성에서 게이트의 남는 입력을 어디에 묶느냐가 결과를 좌우한다. NAND 에 들어가는 값은 이미 반전된 신호이므로, 남는 입력을 1 로 올려 두어야 반전된 0 이 되어 OR 항에서 사라진다. 반대로 0 으로 내리면 그 항이 항상 1 이 되어 NAND 출력이 입력과 무관하게 고정된다.
<empty-block/>
## Active Low 출력과 음논리
이번 주에 쓰는 MSI 부품 두 개는 출력이 Active Low 다. 선택된 출력만 LOW 로 내려가고 나머지는 HIGH 를 유지한다는 뜻이어서, 앞 주차까지의 "출력이 1 이면 켜진다" 와 값의 방향이 반대다. 강의노트도 이 두 회로도에만 Negative Logic 이라고 따로 표시해 두었다.
값의 방향이 뒤집히면 LED 를 다는 방향도 같이 뒤집어야 한다. 출력이 HIGH 일 때 켜지는 회로는 IC 출력이 전류를 밀어내므로 LED 애노드를 IC 쪽에 두지만, 출력이 LOW 일 때 켜지는 회로는 IC 가 전류를 빨아들이므로 애노드를 전원 쪽에 두고 캐소드를 IC 출력에 붙인다. 74HC148 은 여기에 더해 입력까지 Active Low 여서, 스위치를 GND 로 내린 쪽이 그 입력을 활성화한 것이 된다.
<empty-block/>
<empty-block/>
# 실험 부품
## 준비물
<table header-row="true">
<tr>
<td>부품</td>
<td>수량</td>
<td>비고</td>
</tr>
<tr>
<td>74HC04 (hex inverter)</td>
<td>1개</td>
<td>2X4 디코더의 인버터 2개와 Excess-3 인코더의 인버터 6개가 같은 칩을 나눠 쓴다</td>
</tr>
<tr>
<td>74HC08 (quad 2-input AND)</td>
<td>1개</td>
<td>2X4 디코더의 최소항 네 개를 만든다</td>
</tr>
<tr>
<td>74HC20 (dual 4-input NAND)</td>
<td>2개</td>
<td>Excess-3 인코더가 4입력 NAND 를 네 개 쓰는데 패키지에 두 개씩 들어 있다</td>
</tr>
<tr>
<td>74HC42 (BCD-to-decimal decoder)</td>
<td>1개</td>
<td>출력이 Active Low 다</td>
</tr>
<tr>
<td>74HC148 (8-to-3 priority encoder)</td>
<td>1개</td>
<td>입력과 출력이 모두 Active Low 다</td>
</tr>
<tr>
<td>LED</td>
<td>10개</td>
<td>BCD to Decimal 디코더가 열 개를 한꺼번에 쓴다</td>
</tr>
<tr>
<td>저항 330Ω</td>
<td>10개</td>
<td>LED 전류 제한. LED 와 항상 직렬로 넣는다</td>
</tr>
<tr>
<td>SPDT 스위치</td>
<td>8개</td>
<td>입력 인가용. 8X3 우선순위 인코더가 여덟 개를 쓴다</td>
</tr>
<tr>
<td>브레드보드</td>
<td>1개</td>
<td>회로를 꽂는 판</td>
</tr>
<tr>
<td>점퍼선</td>
<td>적당량</td>
<td>전원 레일과 신호 배선</td>
</tr>
</table>
74HC04 는 한 개뿐인데 2X4 디코더가 인버터 두 개를, Excess-3 인코더가 여섯 개를 쓴다. 합이 여덟이라 한 칩에 다 들어가지 않으므로 두 회로를 동시에 올릴 수 없고, 하나를 확인한 뒤 헐고 다음을 세운다. LED 와 저항도 BCD to Decimal 디코더가 열 개를 전부 가져가므로 사정이 같다.
<empty-block/>
## IC 핀 배치
<table header-row="true">
<tr>
<td>IC</td>
<td>패키지</td>
<td>전원 핀</td>
<td>게이트·신호 핀</td>
</tr>
<tr>
<td>74HC04</td>
<td>DIP-14</td>
<td>VCC 14번, GND 7번</td>
<td>1→2, 3→4, 5→6, 9→8, 11→10, 13→12</td>
</tr>
<tr>
<td>74HC08</td>
<td>DIP-14</td>
<td>VCC 14번, GND 7번</td>
<td>1·2→3, 4·5→6, 9·10→8, 12·13→11</td>
</tr>
<tr>
<td>74HC20</td>
<td>DIP-14</td>
<td>VCC 14번, GND 7번</td>
<td>1·2·4·5→6, 9·10·12·13→8 (3번·11번은 내부 미연결)</td>
</tr>
<tr>
<td>74HC42</td>
<td>DIP-16</td>
<td>VCC 16번, GND 8번</td>
<td>입력 A 15번, B 14번, C 13번, D 12번 / 출력 Y0\~Y6 은 1\~7번, Y7 9번, Y8 10번, Y9 11번</td>
</tr>
<tr>
<td>74HC148</td>
<td>DIP-16</td>
<td>VCC 16번, GND 8번</td>
<td>입력 IN0 10번, IN1 11번, IN2 12번, IN3 13번, IN4 1번, IN5 2번, IN6 3번, IN7 4번, EI 5번 / 출력 A0 9번, A1 7번, A2 6번, GS 14번, EO 15번</td>
</tr>
</table>
앞 주차까지는 쓰는 IC 가 모두 DIP-14 여서 전원 핀이 14번과 7번 하나로 통했지만, 이번 주에 새로 나오는 74HC42 와 74HC148 은 DIP-16 이라 16번과 8번이다. 74HC42 의 출력 번호가 7번 다음에 9번으로 건너뛰는 것도 8번이 GND 이기 때문이다.
74HC148 의 전원 핀 번호는 강의노트 회로도에 그려져 있지 않다. 위 표의 16번·8번은 회로도가 쓰는 핀이 1\~7번과 9\~15번이어서 남는 자리가 그 둘뿐이라는 점과 표준 16핀 배치로 잡은 것이므로, 실물 칩의 각인을 확인한 뒤에 전원을 넣는다.
<empty-block/>
<empty-block/>
# 실험 과정 및 예상 결과
## 2X4 디코더 구성
SPDT 스위치 두 개로 `Bit1`·`Bit0` 을 만들고, 74HC04 인버터 두 개로 각각의 보수를 뽑아 74HC08 의 네 게이트에 짝지어 넣는다. 게이트 출력 하나하나가 최소항 하나이므로 `D1 = Bit1·Bit0`, `D2 = Bit1·Bit0'`, `D3 = Bit1'·Bit0`, `D4 = Bit1'·Bit0'` 이 된다.
여기서 LED 번호와 디코딩하는 값의 순서가 서로 거꾸로다. 강의노트 회로도는 위에서부터 D1, D2, D3, D4 로 이름을 붙였지만 이 순서가 가리키는 십진 값은 3, 2, 1, 0 이다. D1 을 1번 출력으로 믿고 기록하면 네 행이 통째로 뒤집힌다.
- **2X4 디코더 예상 진리표**
	<table header-row="true">
<tr>
<td>Bit1</td>
<td>Bit0</td>
<td>D1</td>
<td>D2</td>
<td>D3</td>
<td>D4</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
LED 가 두 개 켜지면 같은 노드를 두 게이트에 잘못 물린 것이고, 하나도 안 켜지면 74HC04 의 전원이나 스위치 공통 단자를 먼저 본다.
<empty-block/>
## BCD to Decimal 디코더
SPDT 스위치 네 개로 `D`·`C`·`B`·`A` 를 만들어 74HC42 에 넣는다. `A` 가 LSB 다. 출력 `Y0` (Active Low) 부터 `Y9` 까지 열 줄에 LED 를 하나씩 달고, 입력을 0 부터 15 까지 올려 가며 어느 줄이 내려가는지 본다.
출력이 Active Low 이므로 각 출력은 대응하는 최소항의 보수다. 곧 `Y0 = (D'·C'·B'·A')'`, `Y1 = (D'·C'·B'·A)'`, `Y2 = (D'·C'·B·A')'`, `Y3 = (D'·C'·B·A)'`, `Y4 = (D'·C·B'·A')'`, `Y5 = (D'·C·B'·A)'`, `Y6 = (D'·C·B·A')'`, `Y7 = (D'·C·B·A)'`, `Y8 = (D·C'·B'·A')'`, `Y9 = (D·C'·B'·A)'` 이다.
- **BCD to Decimal 디코더 예상 진리표 — ****`Y0`****\~****`Y4`**
	<table header-row="true">
<tr>
<td>D</td>
<td>C</td>
<td>B</td>
<td>A</td>
<td>Y0</td>
<td>Y1</td>
<td>Y2</td>
<td>Y3</td>
<td>Y4</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
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
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
- **BCD to Decimal 디코더 예상 진리표 — ****`Y5`****\~****`Y9`**
	<table header-row="true">
<tr>
<td>D</td>
<td>C</td>
<td>B</td>
<td>A</td>
<td>Y5</td>
<td>Y6</td>
<td>Y7</td>
<td>Y8</td>
<td>Y9</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
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
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
표에서 `0` 은 그 출력이 선택되었다는 뜻이고, LED 가 캐소드 쪽으로 물려 있어 그 줄만 켜진다. 아래쪽 여섯 행은 BCD 로 쓰이지 않는 입력이라 열 줄이 모두 HIGH 로 남고 LED 가 하나도 켜지지 않는데, 회로가 죽은 것과 구별하려면 그 직전에 `D C B A = 0000` 을 넣어 `Y0` 이 내려가는지 확인하고 넘어간다.
<empty-block/>
## 10진 / Excess-3 코드 인코더
SPDT 스위치 여섯 개가 십진 0 부터 5 까지를 맡는다. 74HC04 인버터 여섯 개가 각 스위치를 반전하고, 74HC20 의 4입력 NAND 네 개가 그것을 다시 묶어 Excess-3 네 비트를 만든다. 인버터와 NAND 두 단이 곧 OR 이므로 각 출력 비트는 `Bit3 = SW5`, `Bit2 = SW1+SW2+SW3+SW4`, `Bit1 = SW0+SW3+SW4`, `Bit0 = SW0+SW2+SW4` 가 된다.
- **10진 / Excess-3 인코더 예상 진리표**
	<table header-row="true">
<tr>
<td>Decimal</td>
<td>SW5</td>
<td>SW4</td>
<td>SW3</td>
<td>SW2</td>
<td>SW1</td>
<td>SW0</td>
<td>Bit3</td>
<td>Bit2</td>
<td>Bit1</td>
<td>Bit0</td>
</tr>
<tr>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>2</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>3</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>4</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>5</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
이 회로에는 우선순위가 없으므로 스위치는 한 번에 하나만 올린다. 두 개를 함께 올리면 출력이 두 코드의 OR 가 되고, 전부 내리면 `0000` 이 나오는데 이 값은 Excess-3 에 없는 코드다.
<empty-block/>
## 8X3 우선순위 인코더
74HC148 은 입력도 출력도 Active Low 다. 스위치를 GND 로 내린 쪽이 그 입력을 활성화한 것이고, 출력 코드도 해당 번호의 2진수를 반전한 값으로 나온다. 강의노트 회로도에는 `IN0` (Active Low) 과 `IN7` 만 그려져 있지만 나머지 여섯 개도 같은 방식으로 달아 여덟 입력을 모두 쓰고, 강의노트 지시대로 입력을 하나씩만 넣지 말고 여러 개를 동시에 넣어 우선순위를 확인한다. `EI` 는 GND 에 고정하므로 표에서 뺐다.
강의노트는 이 부품의 진리표를 주지 않는다. 아래 표는 74HC148 의 표준 동작으로 미리 적어 둔 것이므로, 실측이 이와 다르면 표를 고치지 말고 실측한 값을 기록한다.
- **8X3 우선순위 인코더 예상 진리표**
	<table header-row="true">
<tr>
<td>IN7</td>
<td>IN6</td>
<td>IN5</td>
<td>IN4</td>
<td>IN3</td>
<td>IN2</td>
<td>IN1</td>
<td>IN0</td>
<td>A2</td>
<td>A1</td>
<td>A0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>0</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>0</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>x</td>
<td>x</td>
<td>x</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>x</td>
<td>x</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>x</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
- **`GS`****·****`EO`**** 예상값**
	<table header-row="true">
<tr>
<td>상태</td>
<td>GS</td>
<td>EO</td>
</tr>
<tr>
<td>활성 입력이 하나도 없다 (표 1행)</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>활성 입력이 하나 이상 있다 (나머지 여덟 행)</td>
<td>0</td>
<td>1</td>
</tr>
	</table>
`x` 는 don't care 로, 더 높은 우선순위의 입력이 이미 잡혀 있어 그 아래 입력을 어떻게 두든 출력이 달라지지 않는다는 뜻이다. 확인할 때는 `IN3` 과 `IN7` 을 같이 내려 출력이 7 쪽으로 나오는지 보고, 3 쪽으로 나오면 우선순위를 거꾸로 배선한 것이다. 첫 행과 마지막 행은 코드 출력이 같으므로 `GS`·`EO` 를 함께 읽어야 두 상태를 가를 수 있다. 두 신호는 아래 표대로 서로 반대로 서므로 둘 중 하나만 봐도 갈리지만, LED 두 개를 나란히 보면 오독이 줄어든다.
<empty-block/>
<empty-block/>
# 회로 결선도
## 공통 결선 규칙
- **패키지별 전원 핀**
	<table header-row="true">
<tr>
<td>패키지</td>
<td>VCC</td>
<td>GND</td>
<td>해당 IC</td>
</tr>
<tr>
<td>DIP-14</td>
<td>14번</td>
<td>7번</td>
<td>74HC04, 74HC08, 74HC20</td>
</tr>
<tr>
<td>DIP-16</td>
<td>16번</td>
<td>8번</td>
<td>74HC42, 74HC148</td>
</tr>
	</table>
앞 주차의 14번·7번 습관대로 16핀 칩에 전원을 물리면 진짜 전원 핀이 떠서 칩이 아예 동작하지 않을 뿐 아니라, 74HC42 의 7번과 74HC148 의 7번·14번이 모두 출력이어서 출력을 전원 레일에 직결하는 셈이 된다. 몸통 길이로는 두 패키지가 잘 구분되지 않으니 핀을 세어서 확인한다.
- **미사용 핀 처리**
	<table header-row="true">
<tr>
<td>상황</td>
<td>처리</td>
<td>이유</td>
</tr>
<tr>
<td>통째로 쓰지 않는 게이트의 입력</td>
<td>GND</td>
<td>입력이 뜨는 것을 막는다</td>
</tr>
<tr>
<td>쓰는 AND·NAND 게이트의 남는 입력</td>
<td>+5V</td>
<td>1 이 AND 의 항등원이다</td>
</tr>
<tr>
<td>쓰는 OR·NOR 게이트의 남는 입력</td>
<td>GND</td>
<td>0 이 OR 의 항등원이다</td>
</tr>
<tr>
<td>내부 미연결 핀 (74HC20 의 3번·11번)</td>
<td>개방</td>
<td>안쪽에 아무것도 붙어 있지 않다</td>
</tr>
<tr>
<td>쓰지 않는 출력 핀</td>
<td>개방</td>
<td>출력끼리 묶거나 레일에 물리면 칩이 상한다</td>
</tr>
	</table>
미사용 입력을 GND 로 내리는 것은 게이트를 통째로 쓰지 않을 때의 처리다. Excess-3 인코더처럼 쓰는 NAND 게이트에 입력이 남는 경우에는 +5V 로 올려야 하고, 습관대로 GND 로 내리면 그 NAND 출력이 입력과 무관하게 1 로 고정된다.
- **항목별 LED 배선 방향**
	<table header-row="true">
<tr>
<td>항목</td>
<td>배선</td>
<td>점등 조건</td>
</tr>
<tr>
<td>2X4 디코더</td>
<td>IC 출력 → 330Ω → LED 애노드, 캐소드 → GND</td>
<td>출력 HIGH</td>
</tr>
<tr>
<td>BCD to Decimal 디코더</td>
<td>+5V → LED 애노드, 캐소드 → 330Ω → IC 출력</td>
<td>출력 LOW</td>
</tr>
<tr>
<td>10진 / Excess-3 인코더</td>
<td>IC 출력 → 330Ω → LED 애노드, 캐소드 → GND</td>
<td>출력 HIGH</td>
</tr>
<tr>
<td>8X3 우선순위 인코더</td>
<td>+5V → LED 애노드, 캐소드 → 330Ω → IC 출력</td>
<td>출력 LOW</td>
</tr>
	</table>
LED 애노드는 긴 다리이고 캐소드는 짧은 다리다. 출력이 LOW 일 때 켜지는 두 회로를 나머지 두 회로와 같은 방향으로 꽂으면 출력이 내려가도 전류가 흐를 길이 없어 아무것도 켜지지 않는다. 330Ω 은 어느 방향이든 빼지 않는다.
입력 스위치는 모두 SPDT 다. 가운데 공통 단자를 IC 입력에 물리고 한쪽 고정 단자를 +5V 에, 다른 쪽을 GND 에 붙인다. 키트에 SPDT 가 없으면 점퍼선을 +5V 나 GND 에 직결하되, 어느 경우에도 입력을 띄워 두지 않는다.
<empty-block/>
## 2X4 디코더 결선
- **2X4 디코더 결선**
	<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
<td>비고</td>
</tr>
<tr>
<td>SW1</td>
<td>공통</td>
<td>`Bit0` 노드</td>
<td>위 접점 +5V, 아래 접점 GND</td>
</tr>
<tr>
<td>SW2</td>
<td>공통</td>
<td>`Bit1` 노드</td>
<td>위 접점 +5V, 아래 접점 GND</td>
</tr>
<tr>
<td>74HC04</td>
<td>14, 7</td>
<td>+5V, GND</td>
<td></td>
</tr>
<tr>
<td>74HC04</td>
<td>1, 2</td>
<td>`Bit0` 입력, `Bit0'` 출력</td>
<td></td>
</tr>
<tr>
<td>74HC04</td>
<td>3, 4</td>
<td>`Bit1` 입력, `Bit1'` 출력</td>
<td></td>
</tr>
<tr>
<td>74HC04</td>
<td>5, 9, 11, 13</td>
<td>GND</td>
<td>남는 인버터 네 개의 입력</td>
</tr>
<tr>
<td>74HC04</td>
<td>6, 8, 10, 12</td>
<td>개방</td>
<td>남는 인버터 네 개의 출력</td>
</tr>
<tr>
<td>74HC08</td>
<td>14, 7</td>
<td>+5V, GND</td>
<td></td>
</tr>
<tr>
<td>74HC08</td>
<td>1, 2 → 3</td>
<td>`Bit0`, `Bit1` → 330Ω → D1 애노드, 캐소드 → GND</td>
<td>`D1 = Bit1·Bit0`, 십진 3</td>
</tr>
<tr>
<td>74HC08</td>
<td>4, 5 → 6</td>
<td>`Bit0'`, `Bit1` → 330Ω → D2 애노드, 캐소드 → GND</td>
<td>`D2 = Bit1·Bit0'`, 십진 2</td>
</tr>
<tr>
<td>74HC08</td>
<td>9, 10 → 8</td>
<td>`Bit0`, `Bit1'` → 330Ω → D3 애노드, 캐소드 → GND</td>
<td>`D3 = Bit1'·Bit0`, 십진 1</td>
</tr>
<tr>
<td>74HC08</td>
<td>12, 13 → 11</td>
<td>`Bit0'`, `Bit1'` → 330Ω → D4 애노드, 캐소드 → GND</td>
<td>`D4 = Bit1'·Bit0'`, 십진 0</td>
</tr>
	</table>
`Bit0` 과 `Bit1` 은 각각 세 곳으로, `Bit0'` 과 `Bit1'` 은 각각 두 곳으로 갈라진다. 브레드보드에서는 스위치 공통 단자와 인버터 출력을 각각 한 줄에 모아 두고 거기서 뽑아 쓰는 편이 배선을 세기 쉽다.
<empty-block/>
## BCD to Decimal 디코더 결선
- **BCD to Decimal 디코더 결선**
	<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
<td>비고</td>
</tr>
<tr>
<td>SW1\~SW4</td>
<td>공통</td>
<td>74HC42 의 15, 14, 13, 12번</td>
<td>위 접점 +5V, 아래 접점 GND</td>
</tr>
<tr>
<td>74HC42</td>
<td>16, 8</td>
<td>+5V, GND</td>
<td>14번·7번이 아니다</td>
</tr>
<tr>
<td>74HC42</td>
<td>15, 14, 13, 12</td>
<td>`A`, `B`, `C`, `D` 입력</td>
<td>`A` 가 LSB</td>
</tr>
<tr>
<td>74HC42</td>
<td>1\~7</td>
<td>`Y0`\~`Y6` → 330Ω → LED 캐소드</td>
<td>LED 애노드는 +5V</td>
</tr>
<tr>
<td>74HC42</td>
<td>9, 10, 11</td>
<td>`Y7`, `Y8`, `Y9` → 330Ω → LED 캐소드</td>
<td>8번이 GND 라 7번 다음이 9번이다</td>
</tr>
	</table>
입력 네 개와 출력 열 개가 모두 쓰이므로 남는 핀이 없다. LED 애노드 열 개는 모두 +5V 레일에 붙고 IC 가 캐소드 쪽에서 전류를 빨아들이는 구조인데, 어느 입력에서도 LOW 로 내려가는 출력이 하나뿐이라 레일 전류는 문제되지 않는다.
<empty-block/>
## 10진 / Excess-3 인코더 결선
- **10진 / Excess-3 인코더 결선**
	<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
<td>비고</td>
</tr>
<tr>
<td>SW0\~SW5</td>
<td>공통</td>
<td>74HC04 의 13, 11, 9, 5, 3, 1번</td>
<td>SW0 이 13번, SW5 가 1번</td>
</tr>
<tr>
<td>74HC04</td>
<td>14, 7</td>
<td>+5V, GND</td>
<td></td>
</tr>
<tr>
<td>74HC04</td>
<td>1→2, 3→4, 5→6</td>
<td>`SW5'`, `SW4'`, `SW3'` 노드</td>
<td></td>
</tr>
<tr>
<td>74HC04</td>
<td>9→8, 11→10, 13→12</td>
<td>`SW2'`, `SW1'`, `SW0'` 노드</td>
<td>인버터 여섯 개를 모두 쓴다</td>
</tr>
<tr>
<td>74HC20 첫 번째</td>
<td>14, 7</td>
<td>+5V, GND</td>
<td></td>
</tr>
<tr>
<td>74HC20 첫 번째</td>
<td>1 / 2, 4, 5 → 6</td>
<td>`SW5'` / +5V → 330Ω → `Bit3` LED 애노드, 캐소드 → GND</td>
<td>남는 입력 세 개를 +5V 로 올린다</td>
</tr>
<tr>
<td>74HC20 첫 번째</td>
<td>9, 10, 12, 13 → 8</td>
<td>`SW4'`, `SW3'`, `SW2'`, `SW1'` → 330Ω → `Bit2` LED 애노드, 캐소드 → GND</td>
<td>입력 네 개를 모두 쓴다</td>
</tr>
<tr>
<td>74HC20 첫 번째</td>
<td>3, 11</td>
<td>개방</td>
<td>내부 미연결</td>
</tr>
<tr>
<td>74HC20 두 번째</td>
<td>14, 7</td>
<td>+5V, GND</td>
<td></td>
</tr>
<tr>
<td>74HC20 두 번째</td>
<td>1, 2, 4 / 5 → 6</td>
<td>`SW4'`, `SW3'`, `SW0'` / +5V → 330Ω → `Bit1` LED 애노드, 캐소드 → GND</td>
<td>남는 입력 하나를 +5V 로 올린다</td>
</tr>
<tr>
<td>74HC20 두 번째</td>
<td>9, 10, 12 / 13 → 8</td>
<td>`SW4'`, `SW2'`, `SW0'` / +5V → 330Ω → `Bit0` LED 애노드, 캐소드 → GND</td>
<td>남는 입력 하나를 +5V 로 올린다</td>
</tr>
<tr>
<td>74HC20 두 번째</td>
<td>3, 11</td>
<td>개방</td>
<td>내부 미연결</td>
</tr>
	</table>
인버터 출력 하나가 여러 NAND 로 갈라진다. `SW4'` 은 세 갈래로 `Bit2`·`Bit1`·`Bit0` 에 모두 들어가고, `SW3'` 과 `SW2'` 과 `SW0'` 은 두 갈래씩, `SW5'` 과 `SW1'` 은 한 갈래다. 배선을 마친 뒤에는 SW0 만 올려 `0011` 이, SW5 만 올려 `1000` 이 나오는지 먼저 본다. SW0 에서 `0000` 이 나오면 `SW0'` 이 어디에도 물리지 않았거나 남는 입력을 GND 로 내린 것이다.
<empty-block/>
## 8X3 우선순위 인코더 결선
- **8X3 우선순위 인코더 결선**
	<table header-row="true">
<tr>
<td>소자</td>
<td>핀</td>
<td>연결</td>
<td>비고</td>
</tr>
<tr>
<td>SW0\~SW7</td>
<td>공통</td>
<td>74HC148 의 10, 11, 12, 13, 1, 2, 3, 4번</td>
<td>아래 접점(GND)으로 내린 쪽이 활성이다</td>
</tr>
<tr>
<td>74HC148</td>
<td>16, 8</td>
<td>+5V, GND</td>
<td>14번은 `GS`, 7번은 `A1` 출력이다</td>
</tr>
<tr>
<td>74HC148</td>
<td>5</td>
<td>GND</td>
<td>`EI`. 띄우면 칩이 동작하지 않는다</td>
</tr>
<tr>
<td>74HC148</td>
<td>9, 7, 6</td>
<td>`A0`, `A1`, `A2` → 330Ω → LED 캐소드</td>
<td>LED 애노드는 +5V</td>
</tr>
<tr>
<td>74HC148</td>
<td>14, 15</td>
<td>`GS`, `EO` → 330Ω → LED 캐소드</td>
<td>LED 애노드는 +5V</td>
</tr>
	</table>
입력 번호와 핀 번호가 연속이 아니다. `IN3` 이 13번인데 그 다음 `IN4` 는 1번으로 건너뛰므로 스위치를 순서대로 꽂다 보면 우선순위 방향이 뒤집히기 쉽다. `EI` 를 GND 에 물린 상태에서는 아무 스위치도 내리지 않아도 `EO` LED 하나가 켜져 있으므로, 이 LED 를 회로가 살아 있다는 표시로 삼는다.
<empty-block/>
## 실험 전 확인할 사항
- 74HC42 와 74HC148 은 DIP-16 이다. 전원을 넣기 전에 두 칩의 8번과 16번을 핀을 세어 짚어 보고, 14번·7번에 전원이 가 있지 않은지 확인한다.
- 74HC148 의 전원 핀 번호는 강의노트에 나와 있지 않으므로 실물 칩의 각인을 읽어 확인한 뒤에 전원을 인가한다.
- 74HC148 의 5번은 GND 에 고정한다. 이 핀이 뜨면 다섯 출력이 모두 꺼져 전원이 안 들어온 것과 똑같이 보인다.
- 74HC20 의 3번과 11번은 내부 미연결이므로 GND 에도 +5V 에도 물리지 않는다.
- Excess-3 인코더에서 NAND 의 남는 입력은 +5V 로 올린다.
- LED 방향이 항목마다 다르다. BCD to Decimal 디코더와 8X3 우선순위 인코더는 애노드가 +5V 쪽이고, 나머지 두 회로는 애노드가 IC 출력 쪽이다.
- 330Ω 은 LED 와 항상 함께 넣는다. 저항 없이 꽂으면 LED 와 IC 출력단이 같이 상한다.
- SPDT 스위치가 없으면 점퍼선을 +5V 나 GND 에 직결하고, 입력을 띄운 채로 두지 않는다.
- 74HC04 는 한 개뿐이라 2X4 디코더와 Excess-3 인코더를 동시에 세울 수 없다. 앞 회로를 확인하고 헐어 낸 뒤 다음 회로를 꽂는다.
<empty-block/>
## 브레드보드 작도
전원 레일과 IC 위치, 스위치와 LED 자리를 아래 판에 미리 그려 두고 실험실에서 그대로 옮겨 꽂는다.
![브레드보드 작도 캔버스]()
<empty-block/>
<empty-block/>
# 출처 및 참고문헌
- 논리회로실험 강의노트