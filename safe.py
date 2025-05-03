import argparse
import json
from enum import Enum

Label = Enum("Label", "CD DD")

class Instruction:
    
    def __init__(self, num: int, info: dict) -> None:
        
        self.num: int = num
        self.info: dict = info
        self.offset: int = info["offset"]
        self.esil: list[str] = info["esil"].split(",")
        # self.refptr: int = info["refptr"]
        self.fcn_addr: int = info["fcn_addr"]   # Offset of function's start
        self.fcn_last: int = info["fcn_last"]   # Offset of function's last instruction
        # self.size: int = info["size"]
        # self.opcode: str = info["opcode"]           
        self.disasm: str = info["disasm"]       # Same as opcode
        # self.bytes: str = info["bytes"]         # Byte repr of opcode
        # self.family: str = info["family"]       # cpu
        self.type: str = info["type"]           # Type of instruction
        # self.reloc: bool = True if info["reloc"] == "true" else False
        # self.type_num: int = info["type_num"]
        # self.type2_num: int = info["type2_num"]

    def print_instruction(self) -> None:
        print(self.type, self.disasm)

def filter_squashing(instr: Instruction) -> bool:
    
    return instr.type in ["mov", "store", "lea"]

    
class IDG:
    
    def __init__(self, id: int) -> None:
        self.id: int = id
        self.children: list["IDG"] = []
    
    def add_edge(self, node: "IDG") -> None:
        self.children.append(node)

class Livetime:
    
    def __init__(self, token: str) -> None:
        self.token: str = token
        self.start: int = -1
        self.end: int = -1
        self.instr: int = -1
        self.use: list[Livetime] = []

class PDG:
    
    def __init__(self, cfg: dict) -> None:
        
        # self.cfg: dict = cfg
        self.name: str = cfg["name"]
        self.size: int = cfg["size"]
        self.addrs: list = cfg["addr"]
        self.ops: list = cfg["ops"]
        self.instructions: list[Instruction] = [Instruction(i, info) for i, info in enumerate(cfg["ops"])]
        self.num_instr: int = len(self.instructions)
        self.offsets: dict[int, int] = {instr.offset: i for i, instr in enumerate(self.instructions)}
        self.adj_list: list[list[tuple[int, Label]]] = [[] for _ in range(self.num_instr)]
        self.tokens = {}
        self.idgs: dict[int, IDG] = {}
        self.ss: dict[int, list[int]] = {}
    
    def get_cd(self) -> None:
        
        for i, instr in enumerate(self.instructions):
            
            if instr.type == "jmp":
                if instr.info["jump"] >= instr.fcn_addr and instr.info["jump"] <= instr.fcn_last:
                    self.adj_list[self.offsets[instr.info["jump"]]].append((i, Label.CD))
            
            elif instr.type == "cjump":
                if instr.info["jump"] >= instr.fcn_addr and instr.info["jump"] <= instr.fcn_last:
                    self.adj_list[self.offsets[instr.info["jump"]]].append((i, Label.CD))
                if instr.info["fail"] >= instr.fcn_addr and instr.info["fail"] <= instr.fcn_last:
                    self.adj_list[self.offsets[instr.info["fail"]]].append((i, Label.CD))
            
            else:
                if i + 1 < self.num_instr:
                    self.adj_list[i + 1].append((i, Label.CD))
    
    def merge_tokens(self, tokens: list[str]) -> None:
        tokens = list(set(tokens))
        
        for i in range(len(tokens)):
            self.tokens[tokens[i]] = i
    
    def get_dd(self) -> None:
        
        tokens: list[str] = []
        
        for i in reversed(range(self.num_instr)):
            instr: Instruction = self.instructions[i]
            
            ind = instr.disasm.find(" ")
            if ind == -1: continue
            operands: list[str] = instr.disasm[ind+1:].split(", ")
            
            for operand in operands:
                tokens.append(operand)
        
        self.merge_tokens(tokens)
        
        livetimes: list[list[Livetime]] = [[] for _ in range(self.num_instr)]
        
        for i in reversed(range(self.num_instr - 1)):
            instr: Instruction = self.instructions[i]
            
            ind = instr.disasm.find(" ")
            if ind == -1: continue
            operands: list[str] = instr.disasm[ind+1:].split(", ")
            
            if len(operands) == 0: continue
            if len(operands) == 1: continue
            
            first: str = operands[0]
            other: list[str] = operands[1:]
            
            for livetime in livetimes[i + 1]:
                if livetime.token == first:
                    livetime.start = i
                    livetime.instr = i
                    livetime.use.extend(livetimes[i + 1])
                else:
                    livetimes[i].append(livetime)
            
            for operand in other:
                if operand not in self.tokens:
                    livetimes[i].append(Livetime(operand))
                    livetimes[i][-1].end = i

        for i in range(self.num_instr - 1):
            for livetime in livetimes[i]:
                if livetime.start == i:
                    for use_lt in livetime.use:
                        if use_lt.instr == i: continue
                        self.adj_list[i].append((use_lt.instr, Label.DD))
        

    def print_cfg(self, f) -> None:
        
        f.write(f"**FUNC: {self.name}\n")
        f.write(f"**BEGIN: CFG\n")
        
        for i, instr in enumerate(self.instructions):
            f.write(f'{self.instructions[i].offset} [{" ".join([str(self.instructions[x[0]].offset) for x in self.adj_list[i]])}] ')
            f.write(f"{instr.disasm}\n")
        
        f.write(f"**END: CFG\n\n")

    def print(self, f) -> None:
        f.write(f"**FUNC: {self.name}\n")
        f.write(f"**BEGIN: SAFE SET\n")
        for i in range(self.num_instr):
            f.write(f"{self.instructions[i].offset}\t{self.ss[i]}\n")
        
        f.write(f"**END: SAFE SET\n\n")

    def get_IDG(self, instr_ind: int) -> None:
        
        self.idgs[instr_ind] = IDG(instr_ind)
        
        for i in self.adj_list[instr_ind]:
            
            if i[1] == Label.DD and self.instructions[i[0]].type in ["mov", "store", "lea"]:
                 continue
            
            if i[0] not in self.idgs:
                self.idgs[i[0]] = IDG(i[0])
                
            self.idgs[instr_ind].add_edge(self.idgs[i[0]])
    
    def get_ancestors(self, instr_ind: int) -> list[int]:
        
        anc: list[int] = []
        mark: list[bool] = [False] * self.num_instr
        stack: list[int] = [instr_ind]
        while stack:
            curr: int = stack.pop()
            if mark[curr]: continue
            mark[curr] = True
            
            for i in self.adj_list[curr]:
                if i[1] == Label.CD:
                    anc.append(i[0])
                    stack.append(i[0])
        
        return anc
    
    def get_descendants(self, idg: IDG) -> list[int]:
        
        desc: list[int] = list(map(lambda x: x.id, idg.children))
        return desc
    
    def get_SS(self) -> None:
        
        for instr_ind in range(self.num_instr):
        
            ancSI: set[int] = set(filter(lambda i: filter_squashing(self.instructions[i]), self.get_ancestors(instr_ind)))
            self.get_IDG(instr_ind)
            deps: set[int] = set(filter(lambda i: filter_squashing(self.instructions[i]), self.get_descendants(self.idgs[instr_ind])))
            self.ss[instr_ind] = list(map(lambda x: self.instructions[x].offset, (ancSI - deps)))
             
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser()
    parser.add_argument("exec_file", type=str)
    parser.add_argument("cfg_file", type=str)
    
    args = parser.parse_args()
    exec_file: str = args.exec_file
    
    cfg_file: str = args.cfg_file
    ss_file: str = exec_file + ".ss"
    pdg_file: str = exec_file + ".pdg"
    
    with open(cfg_file, "r") as f:
        contents = f.read()
    
    if contents is None: exit(0)
    
    pdg: PDG = PDG(json.loads(contents.encode("utf-8")))
    
    pdg.get_cd()
    pdg.get_dd()
    pdg.get_SS()
    
    with open(pdg_file, "a") as f:
        pdg.print_cfg(f)
    
    with open(ss_file, "a") as f:
        pdg.print(f)
    
    
        