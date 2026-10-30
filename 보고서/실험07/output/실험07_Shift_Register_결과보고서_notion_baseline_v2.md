<table_of_contents color="gray"/>
<empty-block/>
# 실험 결과
## 6bit Shift Right Register
74HC00의 NAND 게이트와 74HC76의 JK 플립플롭 여섯 개로 직렬 입력을 BIT1부터 BIT6까지 이동시키는 회로를 구성했다. 각 출력에 연결한 LED가 켜지면 1, 꺼지면 0으로 기록했다.
- **초기화 및 직렬 입력 결과**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>D</td>
<td>CLK</td>
<td>CLR</td>
<td>PR1</td>
<td>PR2</td>
</tr>
<tr>
<td>R0</td>
<td>CLK 정지, 공통 초기화(p9)</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>R1</td>
<td>CLR 해제, 에지 없이 관찰</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S1</td>
<td>D를 설정하고 CLK 0→1→0 하강 직후 관측</td>
<td>1</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S2</td>
<td>D를 설정하고 CLK 0→1→0 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S3</td>
<td>D를 설정하고 CLK 0→1→0 하강 직후 관측</td>
<td>1</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S4</td>
<td>D를 설정하고 CLK 0→1→0 하강 직후 관측</td>
<td>1</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S5</td>
<td>D를 설정하고 CLK 0→1→0 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S6</td>
<td>D를 설정하고 CLK 0→1→0 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
- **출력 상태**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>BIT1</td>
<td>BIT2</td>
<td>BIT3</td>
<td>BIT4</td>
<td>BIT5</td>
<td>BIT6</td>
</tr>
<tr>
<td>R0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>R1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S2</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S3</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S4</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S5</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>S6</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
	</table>
초기화와 여섯 번의 직렬 입력 결과는 예상과 일치했다. 첫 번째로 넣은 1은 여섯 번째 하강 에지 후 BIT6에 도달했다.
- **PR1 강제 SET 및 이동 결과**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>D</td>
<td>CLK</td>
<td>CLR</td>
<td>PR1</td>
<td>PR2</td>
</tr>
<tr>
<td>R0</td>
<td>CLK 정지, 재초기화</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>P1</td>
<td>먼저 CLR=1, 그다음 PR1=0. CLK=0 유지</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>P2</td>
<td>PR1을 1로 해제, 에지 없이 관찰</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S1</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S2</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S3</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S4</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S5</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S6</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
- **출력 상태**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>BIT1</td>
<td>BIT2</td>
<td>BIT3</td>
<td>BIT4</td>
<td>BIT5</td>
<td>BIT6</td>
</tr>
<tr>
<td>R0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>P1</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>P2</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S2</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S3</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S4</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>S5</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>S6</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
PR1을 해제한 뒤 다섯 번째 하강 에지에서 1이 BIT6에 도달했고, 여섯 번째 에지 뒤에는 모든 LED가 꺼졌다.
- **PR2 강제 SET 및 이동 결과**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>조작</td>
<td>D</td>
<td>CLK</td>
<td>CLR</td>
<td>PR1</td>
<td>PR2</td>
</tr>
<tr>
<td>R0</td>
<td>CLK 정지, 재초기화</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>P1</td>
<td>먼저 CLR=1, 그다음 PR2=0. CLK=0 유지</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>P2</td>
<td>PR2를 1로 해제, 에지 없이 관찰</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S1</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S2</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S3</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S4</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
<tr>
<td>S5</td>
<td>CLK을 0→1→0으로 한 번 왕복, 하강 직후 관측</td>
<td>0</td>
<td>1-\>0</td>
<td>1</td>
<td>1</td>
<td>1</td>
</tr>
	</table>
- **출력 상태**
	<table header-row="true">
<tr>
<td>스텝</td>
<td>BIT1</td>
<td>BIT2</td>
<td>BIT3</td>
<td>BIT4</td>
<td>BIT5</td>
<td>BIT6</td>
</tr>
<tr>
<td>R0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>P1</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>P2</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S1</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S2</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
<td>0</td>
</tr>
<tr>
<td>S3</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
<td>0</td>
</tr>
<tr>
<td>S4</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>S5</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
<td>0</td>
</tr>
	</table>
PR2로 만든 1은 해제 후 네 번째 하강 에지에서 BIT6에 도달했고, 다섯 번째 에지 뒤에 빠져나갔다. 두 강제 SET 시험 모두 예상과 일치했다.
<empty-block/>
<empty-block/>
# 실험 사진
예비보고서에서 그린 결선도와 직렬 입력에 따른 LED 점등·소등 장면을 함께 실었다. 아래 사진은 위 표의 입력 순서와는 별도로 촬영한 동작 장면이다.
<empty-block/>
## 6bit Shift Right Register
![예비보고서에서 그린 6bit 시프트 레지스터 결선도](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/0f85a444-1767-48f1-98a2-52b79ea681c4/%EC%8B%A4%ED%97%9807_1_%EC%86%90%EA%B7%B8%EB%A6%BC_6bit%EC%8B%9C%ED%94%84%ED%8A%B8%EB%A0%88%EC%A7%80%EC%8A%A4%ED%84%B0.png)
![직렬 입력을 1로 둔 뒤 LED가 점등되는 장면](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/7f51c332-c794-4260-8263-4185771ca746/01_D1_%EC%84%A4%EB%AA%85_%ED%9B%84_LED_%EC%A0%90%EB%93%B1_%EC%A7%84%ED%96%89.png)
![직렬 입력을 0으로 바꾼 뒤 LED가 소등되는 장면](https://prod-files-secure.s3.us-west-2.amazonaws.com/bb202fe9-e653-4278-8d2f-0d12906a5653/9e3ea12d-a030-4533-8330-028ff5c0cb6b/02_D0_%EB%B3%80%EA%B2%BD_%EC%A0%84%ED%9B%84_LED_%EC%83%81%ED%83%9C.png)
<empty-block/>
<empty-block/>
# 예비보고서와의 비교
공통 CLR을 0으로 두었을 때 여섯 비트가 모두 0이 되었고, CLR을 해제한 뒤에도 클럭 에지가 없으므로 그 상태가 유지됐다. 이는 비동기 초기화와 상태 유지에 대한 예상과 일치한다.
직렬 입력 시험에서는 각 하강 에지 뒤에 새 입력이 BIT1에 들어오고 기존 값은 다음 비트로 이동했다. 예를 들어 S4의 출력 110100은 다음 에지에서 D=0이 입력되자 011010이 됐다. S6에서는 처음 입력한 1이 BIT6에 도달해 여섯 단을 거치는 과정을 확인할 수 있었다.
PR1과 PR2 시험에서도 예상한 위치에 1이 만들어졌다. 클럭을 정지한 채 PR1 또는 PR2를 0으로 두면 각각 BIT1 또는 BIT2가 1이 됐고, 해당 입력을 해제한 후에도 에지가 없을 때는 상태가 유지됐다. 이후 D=0으로 클럭을 주자 1이 한 단씩 이동해 마지막에는 모든 비트가 0이 됐다.
<empty-block/>
<empty-block/>
# 결과 분석
JK 플립플롭은 J=1, K=0일 때 1로 SET되고 J=0, K=1일 때 0으로 RESET된다. 첫 단은 J에 D를, K에 NAND 게이트로 반전한 D를 받으므로 클럭의 하강 에지에서 D가 1이면 1을, D가 0이면 0을 저장한다.
나머지 단은 앞단의 Q와 Q'를 각각 J와 K에 받는다. 따라서 각 단은 하강 에지 직전 앞단에 저장된 값을 받아들인다. 모든 단이 공통 클럭을 받더라도 각 에지에서 이전 상태를 기준으로 값이 전달되므로 한 번에 한 단씩 이동한다. 직렬 입력 시험의 S4에서 S5로 넘어갈 때 BIT1에 새로 들어온 0과 기존 11010의 이동을 함께 볼 수 있다.
공통 CLR과 PR1·PR2는 클럭과 관계없이 동작하는 비동기 입력이며 0일 때 활성화된다. CLR=0이면 출력이 초기화되고, CLR을 해제한 뒤 PR1 또는 PR2를 0으로 두면 각각 BIT1 또는 BIT2가 SET된다. SET 입력을 1로 되돌린 다음에는 저장된 1이 후속 하강 에지마다 이동한다. 두 시험에서 BIT6까지 필요한 에지 수가 각각 다섯 번과 네 번인 것은 1이 시작한 위치가 한 단 다르기 때문이다.
처음에는 직렬 입력과 PR1 강제 주입을 시도해도 LED가 켜지지 않았다. LED를 따로 확인했을 때는 문제가 없었고, 첫 두 플립플롭이 들어 있는 U2가 제대로 꽂혀 있지 않은 것을 발견했다. U2를 다시 꽂은 뒤 두 방법에서 LED가 켜졌다. U2가 제대로 꽂히지 않아 회로가 동작하지 않았던 것으로 보인다.
<empty-block/>
<empty-block/>
# 고찰
초기화 후 직렬 입력과 두 SET 입력을 각각 시험하면서 한 회로에서 데이터를 넣는 방법과 저장된 값이 이동하는 과정을 확인할 수 있었다. 특히 클럭을 멈춘 상태에서 SET한 값이 입력을 해제한 뒤에도 유지되고, 이후 클럭에 따라 이동하는 점이 인상적이었다.
처음에는 직렬 입력과 PR1 강제 주입에서 LED가 켜지지 않아 회로를 확인하는 데 막혔다. LED를 따로 검사하고 U2의 삽입 상태를 확인했으며, U2를 다시 꽂은 뒤 두 방법으로 점등을 확인했다. 이 과정에서 예상과 다른 결과가 나왔을 때 소자 자체뿐 아니라 브레드보드에 제대로 삽입되어 있는지도 살펴볼 필요가 있음을 알게 됐다.
<empty-block/>
<empty-block/>
# 추가 공부
## IC 삽입 상태와 순차회로의 확인
첫 단이 동작하지 않으면 뒤 단에 전달할 데이터도 생기지 않으므로 여러 LED가 함께 꺼져 있어도 모든 플립플롭이 불량이라고 판단할 수는 없다. 전원과 접지, IC 삽입 상태를 확인한 다음 첫 단의 입력과 출력을 살피고 뒤 단으로 범위를 넓히면 고장 지점을 좁힐 수 있다. 이번에는 제대로 꽂히지 않은 U2를 다시 꽂은 뒤 동작이 회복됐다.
<empty-block/>
## 출력 부하와 논리 레벨
BIT1\~BIT5의 Q 출력은 LED 회로와 다음 단의 J 입력을 함께 구동하고, 마지막 BIT6의 Q 출력은 LED 회로에 연결된다. 출력에 부하가 걸리면 출력 전압이 변할 수 있으므로 LED가 켜진다는 사실만으로 다음 단이 충분한 여유를 두고 1을 인식한다고 단정할 수는 없다.
이를 판단하려면 해당 제조사의 데이터시트에서 출력 전류에 따른 출력 전압 보증 조건과 다음 단의 입력 전압 조건을 비교해야 한다. 실제 회로에서도 부하가 연결된 상태의 전압을 측정해야 한다. 이번 실험의 LED 관찰은 논리 상태의 이동을 보여 주지만, 그 자체로 전압 여유나 최대 동작 속도를 측정한 것은 아니다.
<empty-block/>
<empty-block/>
# 출처 및 참고문헌
- 논리회로실험 강의노트
- 논리회로실험 IC 특성 분석 가이드
- Nexperia. 74HC00; 74HCT00, Quad 2-input NAND gate. 문서번호 74HC_HCT00, Rev. 11, 2025-04-29. [https://assets.nexperia.com/documents/data-sheet/74HC_HCT00.pdf](https://assets.nexperia.com/documents/data-sheet/74HC_HCT00.pdf)
- Renesas Electronics. HD74HC76, Dual J-K Flip-Flops (with Preset and Clear). 문서번호 REJ03D0551-0200 (Previous ADE-205-423), Rev. 2.00, 2005-10-06. [https://www.renesas.com/en/document/dst/hd74hc76-datasheet](https://www.renesas.com/en/document/dst/hd74hc76-datasheet)